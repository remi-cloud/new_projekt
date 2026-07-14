import type { ChartCandle } from '../types/chart'

export type LiquiditySide = 'buy-side' | 'sell-side'
export type LiquidityKind = 'equal-highs' | 'equal-lows' | 'swing-high' | 'swing-low'

export interface SwingPoint {
  index: number
  time: number
  price: number
}

export interface LiquidityZone {
  id: string
  price: number
  side: LiquiditySide
  kind: LiquidityKind
  touches: number
  strength: number
  swept: boolean
  firstTime: number
  lastTime: number
  label: string
}

export interface LiquidityScanResult {
  zones: LiquidityZone[]
  nearestAbove: LiquidityZone | null
  nearestBelow: LiquidityZone | null
  currentPrice: number
  swingHighCount: number
  swingLowCount: number
}

const KIND_LABEL: Record<LiquidityKind, string> = {
  'equal-highs': 'EQH',
  'equal-lows': 'EQL',
  'swing-high': 'SH',
  'swing-low': 'SL',
}

export function findSwingHighs(candles: ChartCandle[], left = 3, right = 3): SwingPoint[] {
  const out: SwingPoint[] = []
  for (let i = left; i < candles.length - right; i++) {
    const h = candles[i].high
    let isSwing = true
    for (let j = i - left; j <= i + right; j++) {
      if (j !== i && candles[j].high >= h) {
        isSwing = false
        break
      }
    }
    if (isSwing) out.push({ index: i, time: candles[i].time, price: h })
  }
  return out
}

export function findSwingLows(candles: ChartCandle[], left = 3, right = 3): SwingPoint[] {
  const out: SwingPoint[] = []
  for (let i = left; i < candles.length - right; i++) {
    const l = candles[i].low
    let isSwing = true
    for (let j = i - left; j <= i + right; j++) {
      if (j !== i && candles[j].low <= l) {
        isSwing = false
        break
      }
    }
    if (isSwing) out.push({ index: i, time: candles[i].time, price: l })
  }
  return out
}

function avgRangePct(candles: ChartCandle[], n = 20): number {
  if (!candles.length) return 0.001
  const slice = candles.slice(-Math.min(n, candles.length))
  const avg =
    slice.reduce((s, c) => s + (c.high - c.low) / Math.max(c.close, 1e-9), 0) / slice.length
  return Math.max(avg * 0.4, 0.0005)
}

interface RawZone {
  price: number
  side: LiquiditySide
  kind: LiquidityKind
  touches: number
  firstTime: number
  lastTime: number
}

function clusterSwings(
  swings: SwingPoint[],
  tolerancePct: number,
  baseKind: 'swing-high' | 'swing-low',
  side: LiquiditySide,
): RawZone[] {
  if (!swings.length) return []

  const sorted = [...swings].sort((a, b) => a.price - b.price)
  const clusters: SwingPoint[][] = []

  for (const sw of sorted) {
    let placed = false
    for (const cl of clusters) {
      const avg = cl.reduce((s, p) => s + p.price, 0) / cl.length
      if (Math.abs(sw.price - avg) / avg <= tolerancePct) {
        cl.push(sw)
        placed = true
        break
      }
    }
    if (!placed) clusters.push([sw])
  }

  return clusters.map((cl) => {
    const touches = cl.length
    const price = cl.reduce((s, p) => s + p.price, 0) / touches
    const times = cl.map((p) => p.time)
    const kind: LiquidityKind =
      touches >= 2 ? (baseKind === 'swing-high' ? 'equal-highs' : 'equal-lows') : baseKind
    return {
      price,
      side,
      kind,
      touches,
      firstTime: Math.min(...times),
      lastTime: Math.max(...times),
    }
  })
}

function isSwept(zone: RawZone, candles: ChartCandle[]): boolean {
  const after = candles.filter((c) => c.time > zone.lastTime)
  if (!after.length) return false
  if (zone.side === 'sell-side') {
    return after.some((c) => c.high > zone.price * 1.0001)
  }
  return after.some((c) => c.low < zone.price * 0.9999)
}

function zoneStrength(zone: RawZone & { swept: boolean }, candles: ChartCandle[]): number {
  const lastTime = candles[candles.length - 1].time
  const firstTime = candles[0].time
  const span = Math.max(lastTime - firstTime, 1)
  const recency = (zone.lastTime - firstTime) / span

  let s = Math.min(zone.touches, 5) * 14
  if (zone.kind === 'equal-highs' || zone.kind === 'equal-lows') s += 22
  if (!zone.swept) s += 24
  s += Math.round(recency * 18)
  return Math.min(100, s)
}

export function scanLiquidity(candles: ChartCandle[]): LiquidityScanResult | null {
  if (candles.length < 24) return null

  const currentPrice = candles[candles.length - 1].close
  const tolerance = avgRangePct(candles)

  const swingHighs = findSwingHighs(candles)
  const swingLows = findSwingLows(candles)

  const raw: RawZone[] = [
    ...clusterSwings(swingHighs, tolerance, 'swing-high', 'sell-side'),
    ...clusterSwings(swingLows, tolerance, 'swing-low', 'buy-side'),
  ]

  let zones: LiquidityZone[] = raw.map((z, i) => {
    const swept = isSwept(z, candles)
    const label = `${KIND_LABEL[z.kind]}×${z.touches}`
    return {
      id: `${z.side}-${i}-${z.price.toFixed(4)}`,
      ...z,
      swept,
      strength: zoneStrength({ ...z, swept }, candles),
      label,
    }
  })

  zones = zones
    .filter((z) => Math.abs(z.price - currentPrice) / currentPrice <= 0.15)
    .sort((a, b) => {
      if (a.swept !== b.swept) return a.swept ? 1 : -1
      return b.strength - a.strength
    })
    .slice(0, 8)

  const above = zones
    .filter((z) => z.side === 'sell-side' && z.price > currentPrice)
    .sort((a, b) => a.price - b.price)
  const below = zones
    .filter((z) => z.side === 'buy-side' && z.price < currentPrice)
    .sort((a, b) => b.price - a.price)

  return {
    zones,
    nearestAbove: above[0] ?? null,
    nearestBelow: below[0] ?? null,
    currentPrice,
    swingHighCount: swingHighs.length,
    swingLowCount: swingLows.length,
  }
}

export function formatLiquidityPrice(price: number): string {
  if (price >= 1000) return price.toFixed(2)
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}
