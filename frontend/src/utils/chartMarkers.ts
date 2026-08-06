import type { PaperTrade } from '../types'
import type { ChartCandle, CycleMarker } from '../types/chart'
import type { SeriesMarker, Time, UTCTimestamp } from 'lightweight-charts'

export interface ChartMarkerLabels {
  cycleEntry: string
  cycleExit: string
  shortOngoing: string
  tradeBuy: string
  tradeSell: string
  positionOpen: string
}

const DEFAULT_LABELS: ChartMarkerLabels = {
  cycleEntry: 'ENT',
  cycleExit: 'EXT',
  shortOngoing: 'SHORT',
  tradeBuy: 'BUY',
  tradeSell: 'SEL',
  positionOpen: 'OPN',
}

function snapToCandle(ts: number, candles: ChartCandle[]): number | null {
  if (!candles.length) return null
  const exact = candles.find((c) => c.time === ts)
  if (exact) return exact.time

  let best = candles[0].time
  let bestDiff = Math.abs(ts - best)
  for (const c of candles) {
    const diff = Math.abs(c.time - ts)
    if (diff < bestDiff) {
      bestDiff = diff
      best = c.time
    }
  }
  return best
}

function formatMarkerDate(ts: number): string {
  const d = new Date(ts * 1000)
  const day = String(d.getUTCDate()).padStart(2, '0')
  const month = String(d.getUTCMonth() + 1).padStart(2, '0')
  return `${day}.${month}`
}

const ACTION_RANK: Record<CycleMarker['action'], number> = {
  buy: 3,
  sell: 2,
  watch: 1,
  hold: 0,
}

function markerFromCycle(
  m: CycleMarker,
  snapped: number,
  labels: ChartMarkerLabels,
): SeriesMarker<Time> {
  const dateLabel = formatMarkerDate(snapped)
  if (m.action === 'watch') {
    return {
      time: snapped as UTCTimestamp,
      position: 'aboveBar',
      color: '#94a3b8',
      shape: 'circle',
      text: `${labels.shortOngoing} ${dateLabel}`,
    }
  }
  const isBuy = m.action === 'buy'
  return {
    time: snapped as UTCTimestamp,
    position: isBuy ? 'belowBar' : 'aboveBar',
    color: isBuy ? '#22c55e' : '#f97316',
    shape: isBuy ? 'arrowUp' : 'arrowDown',
    text: isBuy ? `${labels.cycleEntry} ${dateLabel}` : `${labels.cycleExit} ${dateLabel}`,
  }
}

export function cycleMarkersToChartMarkers(
  markers: CycleMarker[],
  candles: ChartCandle[],
  labels: ChartMarkerLabels = DEFAULT_LABELS,
): SeriesMarker<Time>[] {
  if (!markers.length || !candles.length) return []

  const minT = candles[0].time
  const maxT = candles[candles.length - 1].time
  // Prefer buy > sell > watch on the same snapped candle (matches backend _dedupe_markers).
  // hold is ignored — never painted as SHORT.
  const byTime = new Map<number, CycleMarker>()

  for (const m of markers) {
    if (m.action === 'hold') continue
    const snapped = snapToCandle(m.time, candles)
    if (snapped === null || snapped < minT || snapped > maxT) continue
    const prev = byTime.get(snapped)
    if (!prev || (ACTION_RANK[m.action] ?? 0) >= (ACTION_RANK[prev.action] ?? 0)) {
      byTime.set(snapped, m)
    }
  }

  const out = [...byTime.entries()]
    .map(([snapped, m]) => markerFromCycle(m, snapped, labels))
    .sort((a, b) => (a.time as number) - (b.time as number))
  return out
}

export function tradesToChartMarkers(
  trades: PaperTrade[],
  candles: ChartCandle[],
  labels: ChartMarkerLabels = DEFAULT_LABELS,
): SeriesMarker<Time>[] {
  if (!trades.length || !candles.length) return []

  const minT = candles[0].time
  const maxT = candles[candles.length - 1].time
  const markers: SeriesMarker<Time>[] = []

  for (const t of trades) {
    const ts = Math.floor(new Date(t.created_at).getTime() / 1000)
    const snapped = snapToCandle(ts, candles)
    if (snapped === null || snapped < minT || snapped > maxT) continue
    const isBuy = t.side === 'buy'
    const qty =
      t.quantity >= 1
        ? t.quantity % 1 === 0
          ? String(t.quantity)
          : t.quantity.toFixed(2)
        : t.quantity.toFixed(4)
    markers.push({
      time: snapped as UTCTimestamp,
      position: isBuy ? 'belowBar' : 'aboveBar',
      color: isBuy ? '#10b981' : '#ef4444',
      shape: isBuy ? 'arrowUp' : 'arrowDown',
      text: isBuy ? `${labels.tradeBuy} ${qty}` : `${labels.tradeSell} ${qty}`,
    })
  }

  markers.sort((a, b) => (a.time as number) - (b.time as number))
  return markers
}

export function positionOpenMarker(
  openedAt: string,
  candles: ChartCandle[],
  labels: ChartMarkerLabels = DEFAULT_LABELS,
): SeriesMarker<Time>[] {
  if (!openedAt || !candles.length) return []
  const ts = Math.floor(new Date(openedAt).getTime() / 1000)
  const snapped = snapToCandle(ts, candles)
  if (snapped === null) return []
  const minT = candles[0].time
  const maxT = candles[candles.length - 1].time
  if (snapped < minT || snapped > maxT) return []
  return [
    {
      time: snapped as UTCTimestamp,
      position: 'belowBar',
      color: '#3b82f6',
      shape: 'circle',
      text: labels.positionOpen,
    },
  ]
}
