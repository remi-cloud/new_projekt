import type { ChartCandle } from '../types/chart'
import type { UTCTimestamp } from 'lightweight-charts'

export interface RsiPoint {
  time: UTCTimestamp
  value: number
}

export interface RsiSeries {
  points: RsiPoint[]
  latest: number | null
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

export function computeRsiSeries(candles: ChartCandle[]): RsiSeries {
  if (candles.length < 3) return { points: [], latest: null }

  const closes = candles.map((c) => c.close)
  const rsiVals = rsi(closes, 14)
  const points: RsiPoint[] = []

  for (let i = 0; i < candles.length; i++) {
    const rv = rsiVals[i]
    if (rv !== null && Number.isFinite(rv)) {
      points.push({ time: candles[i].time as UTCTimestamp, value: Math.round(rv * 10) / 10 })
    }
  }

  return { points, latest: points.length ? points[points.length - 1].value : null }
}
