import { describe, expect, it } from 'vitest'
import type { ChartCandle } from '../types/chart'
import {
  computeAtrSeries,
  computeBollingerSeries,
  computeEmaSeries,
  computeMacdSeries,
  computeRsiSeries,
  computeSmaSeries,
  computeVolumeSeries,
} from './chartIndicators'

function makeCandles(n: number, start = 100): ChartCandle[] {
  const out: ChartCandle[] = []
  let price = start
  for (let i = 0; i < n; i++) {
    const open = price
    price = price + (i % 3 === 0 ? -1.5 : 1.2)
    const close = price
    const high = Math.max(open, close) + 0.8
    const low = Math.min(open, close) - 0.8
    out.push({
      time: 1_700_000_000 + i * 3600,
      open,
      high,
      low,
      close,
      volume: 1000 + i * 10,
    })
  }
  return out
}

describe('chartIndicators', () => {
  const candles = makeCandles(80)

  it('computes SMA/EMA with expected lengths', () => {
    expect(computeSmaSeries(candles, 20).length).toBeGreaterThan(50)
    expect(computeEmaSeries(candles, 20).length).toBeGreaterThan(50)
  })

  it('computes Bollinger mid between bands', () => {
    const bb = computeBollingerSeries(candles)
    expect(bb.length).toBeGreaterThan(0)
    const last = bb[bb.length - 1]
    expect(last.upper).toBeGreaterThan(last.mid)
    expect(last.mid).toBeGreaterThan(last.lower)
  })

  it('computes RSI in 0–100', () => {
    const rsi = computeRsiSeries(candles)
    expect(rsi.latest).not.toBeNull()
    expect(rsi.latest!).toBeGreaterThanOrEqual(0)
    expect(rsi.latest!).toBeLessThanOrEqual(100)
  })

  it('computes MACD with hist = macd - signal', () => {
    const macd = computeMacdSeries(candles)
    expect(macd.latest).not.toBeNull()
    const p = macd.latest!
    expect(Math.abs(p.hist - (p.macd - p.signal))).toBeLessThan(1e-9)
  })

  it('computes ATR and volume', () => {
    const atr = computeAtrSeries(candles)
    expect(atr.length).toBeGreaterThan(0)
    expect(atr[atr.length - 1].value).toBeGreaterThan(0)
    expect(computeVolumeSeries(candles)).toHaveLength(candles.length)
  })
})
