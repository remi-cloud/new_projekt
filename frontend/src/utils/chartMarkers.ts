import type { PaperTrade } from '../types'
import type { ChartCandle } from '../types/chart'
import type { SeriesMarker, Time, UTCTimestamp } from 'lightweight-charts'

export function tradesToChartMarkers(trades: PaperTrade[], candles: ChartCandle[]): SeriesMarker<Time>[] {
  if (!trades.length || !candles.length) return []

  const minT = candles[0].time
  const maxT = candles[candles.length - 1].time
  const markers: SeriesMarker<Time>[] = []

  for (const t of trades) {
    const ts = Math.floor(new Date(t.created_at).getTime() / 1000)
    if (ts < minT || ts > maxT) continue
    const isBuy = t.side === 'buy'
    const qty =
      t.quantity >= 1
        ? t.quantity % 1 === 0
          ? String(t.quantity)
          : t.quantity.toFixed(2)
        : t.quantity.toFixed(4)
    markers.push({
      time: ts as UTCTimestamp,
      position: isBuy ? 'belowBar' : 'aboveBar',
      color: isBuy ? '#10b981' : '#ef4444',
      shape: isBuy ? 'arrowUp' : 'arrowDown',
      text: isBuy ? `KUP ${qty}` : `SPR ${qty}`,
    })
  }

  markers.sort((a, b) => (a.time as number) - (b.time as number))
  return markers
}
