import type { ChartCandle } from '../types/chart'
import type { UTCTimestamp } from 'lightweight-charts'

export interface IndicatorPoint {
  time: UTCTimestamp
  value: number
}

export interface RsiPoint extends IndicatorPoint {}

export interface RsiSeries {
  points: RsiPoint[]
  latest: number | null
}

export interface MacdPoint {
  time: UTCTimestamp
  macd: number
  signal: number
  hist: number
}

export interface MacdSeries {
  points: MacdPoint[]
  latest: MacdPoint | null
}

export interface BollingerPoint {
  time: UTCTimestamp
  mid: number
  upper: number
  lower: number
}

export interface VolumePoint {
  time: UTCTimestamp
  value: number
  color: string
}

export type ChartIndicatorId = 'rsi' | 'sma' | 'ema' | 'bb' | 'volume' | 'macd' | 'atr'

export interface ChartIndicatorFlags {
  rsi?: boolean
  sma?: boolean
  ema?: boolean
  bb?: boolean
  volume?: boolean
  macd?: boolean
  atr?: boolean
}

export const DEFAULT_CHART_INDICATORS: Required<ChartIndicatorFlags> = {
  rsi: false,
  sma: true,
  ema: false,
  bb: false,
  volume: true,
  macd: false,
  atr: true,
}

export const CYCLES_CHART_INDICATORS: Required<ChartIndicatorFlags> = {
  rsi: true,
  sma: true,
  ema: false,
  bb: false,
  volume: true,
  macd: true,
  atr: true,
}

function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = []
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= period) sum -= values[i - period]
    if (i + 1 < period) out.push(null)
    else out.push(sum / period)
  }
  return out
}

function ema(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = []
  if (!values.length) return out
  const k = 2 / (period + 1)
  let prev: number | null = null
  let seed = 0
  for (let i = 0; i < values.length; i++) {
    if (i < period) {
      seed += values[i]
      if (i + 1 < period) {
        out.push(null)
        continue
      }
      prev = seed / period
      out.push(prev)
      continue
    }
    prev = values[i] * k + (prev as number) * (1 - k)
    out.push(prev)
  }
  return out
}

function rsi(values: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = []
  if (values.length < period + 1) return values.map(() => null)

  let avgGain = 0
  let avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const diff = values[i] - values[i - 1]
    if (diff >= 0) avgGain += diff
    else avgLoss -= diff
  }
  avgGain /= period
  avgLoss /= period

  for (let i = 0; i < period; i++) out.push(null)

  const pushRsi = (g: number, l: number) => {
    if (l === 0) out.push(100)
    else out.push(100 - 100 / (1 + g / l))
  }
  pushRsi(avgGain, avgLoss)

  for (let i = period + 1; i < values.length; i++) {
    const diff = values[i] - values[i - 1]
    const gain = diff > 0 ? diff : 0
    const loss = diff < 0 ? -diff : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
    pushRsi(avgGain, avgLoss)
  }
  return out
}

function toPoints(candles: ChartCandle[], values: (number | null)[]): IndicatorPoint[] {
  const points: IndicatorPoint[] = []
  for (let i = 0; i < candles.length; i++) {
    const v = values[i]
    if (v != null && Number.isFinite(v)) {
      points.push({ time: candles[i].time as UTCTimestamp, value: v })
    }
  }
  return points
}

export function computeRsiSeries(candles: ChartCandle[], period = 14): RsiSeries {
  if (candles.length < 3) return { points: [], latest: null }
  const closes = candles.map((c) => c.close)
  const rsiVals = rsi(closes, period)
  const points = toPoints(candles, rsiVals).map((p) => ({
    ...p,
    value: Math.round(p.value * 10) / 10,
  }))
  return { points, latest: points.length ? points[points.length - 1].value : null }
}

export function computeSmaSeries(candles: ChartCandle[], period: number): IndicatorPoint[] {
  if (candles.length < period) return []
  return toPoints(
    candles,
    sma(
      candles.map((c) => c.close),
      period,
    ),
  )
}

export function computeEmaSeries(candles: ChartCandle[], period: number): IndicatorPoint[] {
  if (candles.length < period) return []
  return toPoints(
    candles,
    ema(
      candles.map((c) => c.close),
      period,
    ),
  )
}

export function computeBollingerSeries(
  candles: ChartCandle[],
  period = 20,
  mult = 2,
): BollingerPoint[] {
  if (candles.length < period) return []
  const closes = candles.map((c) => c.close)
  const mids = sma(closes, period)
  const out: BollingerPoint[] = []
  for (let i = 0; i < candles.length; i++) {
    const mid = mids[i]
    if (mid == null) continue
    let sumSq = 0
    for (let j = i - period + 1; j <= i; j++) {
      const d = closes[j] - mid
      sumSq += d * d
    }
    const std = Math.sqrt(sumSq / period)
    out.push({
      time: candles[i].time as UTCTimestamp,
      mid,
      upper: mid + mult * std,
      lower: mid - mult * std,
    })
  }
  return out
}

export function computeMacdSeries(
  candles: ChartCandle[],
  fast = 12,
  slow = 26,
  signalPeriod = 9,
): MacdSeries {
  if (candles.length < slow + signalPeriod) return { points: [], latest: null }
  const closes = candles.map((c) => c.close)
  const emaFast = ema(closes, fast)
  const emaSlow = ema(closes, slow)
  const macdLine: (number | null)[] = closes.map((_, i) => {
    const f = emaFast[i]
    const s = emaSlow[i]
    if (f == null || s == null) return null
    return f - s
  })
  const signalLine: (number | null)[] = macdLine.map(() => null)
  const compact: number[] = []
  const compactIdx: number[] = []
  for (let i = 0; i < macdLine.length; i++) {
    if (macdLine[i] != null) {
      compact.push(macdLine[i] as number)
      compactIdx.push(i)
    }
  }
  if (compact.length) {
    const sigCompact = ema(compact, signalPeriod)
    for (let j = 0; j < compact.length; j++) {
      const sv = sigCompact[j]
      if (sv != null) signalLine[compactIdx[j]] = sv
    }
  }

  const points: MacdPoint[] = []
  for (let i = 0; i < candles.length; i++) {
    const m = macdLine[i]
    const s = signalLine[i]
    if (m == null || s == null) continue
    points.push({
      time: candles[i].time as UTCTimestamp,
      macd: m,
      signal: s,
      hist: m - s,
    })
  }
  return { points, latest: points.length ? points[points.length - 1] : null }
}

export function computeAtrSeries(candles: ChartCandle[], period = 14): IndicatorPoint[] {
  if (candles.length < period + 1) return []
  const tr: number[] = [0]
  for (let i = 1; i < candles.length; i++) {
    const h = candles[i].high
    const l = candles[i].low
    const prevClose = candles[i - 1].close
    tr.push(Math.max(h - l, Math.abs(h - prevClose), Math.abs(l - prevClose)))
  }
  const atrVals: (number | null)[] = []
  let sum = 0
  for (let i = 0; i < candles.length; i++) {
    if (i === 0) {
      atrVals.push(null)
      continue
    }
    sum += tr[i]
    if (i < period) {
      atrVals.push(null)
      continue
    }
    if (i === period) {
      atrVals.push(sum / period)
      continue
    }
    const prev = atrVals[i - 1] as number
    atrVals.push((prev * (period - 1) + tr[i]) / period)
  }
  return toPoints(candles, atrVals)
}

export function computeVolumeSeries(candles: ChartCandle[]): VolumePoint[] {
  const out: VolumePoint[] = []
  for (const c of candles) {
    const v = c.volume
    if (v == null || !Number.isFinite(v) || v < 0) continue
    const up = c.close >= c.open
    out.push({
      time: c.time as UTCTimestamp,
      value: v,
      color: up ? 'rgba(50, 215, 75, 0.35)' : 'rgba(255, 69, 58, 0.35)',
    })
  }
  return out
}

export function latestValue(points: IndicatorPoint[]): number | null {
  return points.length ? points[points.length - 1].value : null
}
