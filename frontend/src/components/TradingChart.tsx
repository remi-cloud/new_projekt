import { useEffect, useRef, useState } from 'react'
import {
  ColorType,
  CrosshairMode,
  createChart,
  UTCTimestamp,
} from 'lightweight-charts'
import { fetchChart } from '../api'
import { ChartCandle, ChartPreset, ChartResponse } from '../types/chart'

interface TradingChartProps {
  candles: ChartCandle[]
  height?: number
  mode?: 'area' | 'candle'
  positive?: boolean
}

export function TradingChart({
  candles,
  height = 140,
  mode = 'area',
  positive = true,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || !candles.length) return

    const upColor = '#10b981'
    const downColor = '#ef4444'
    const lineColor = positive ? upColor : downColor

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#64748b',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(45,55,72,0.35)' },
        horzLines: { color: 'rgba(45,55,72,0.35)' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(45,55,72,0.5)' },
      timeScale: { borderColor: 'rgba(45,55,72,0.5)', timeVisible: mode === 'candle' },
      handleScroll: mode === 'candle',
      handleScale: mode === 'candle',
    })

    if (mode === 'candle') {
      const series = chart.addCandlestickSeries({
        upColor,
        downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor,
      })
      series.setData(
        candles.map((c) => ({
          time: c.time as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      )
    } else {
      const series = chart.addAreaSeries({
        lineColor,
        topColor: positive ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)',
        bottomColor: positive ? 'rgba(16,185,129,0.02)' : 'rgba(239,68,68,0.02)',
        lineWidth: 2,
      })
      series.setData(
        candles.map((c) => ({
          time: c.time as UTCTimestamp,
          value: c.close,
        })),
      )
    }

    chart.timeScale().fitContent()

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [candles, height, mode, positive])

  if (!candles.length) {
    return <div className="chart-empty" style={{ height }}>Brak danych wykresu</div>
  }

  return <div className="trading-chart" ref={containerRef} />
}

interface ChartLoaderProps {
  symbol: string
  preset?: ChartPreset
  height?: number
  mode?: 'area' | 'candle'
  enabled?: boolean
  onData?: (data: ChartResponse) => void
}

export function ChartLoader({
  symbol,
  preset = '3M',
  height = 140,
  mode = 'area',
  enabled = true,
  onData,
}: ChartLoaderProps) {
  const [candles, setCandles] = useState<ChartCandle[]>([])
  const [loading, setLoading] = useState(false)
  const [positive, setPositive] = useState(true)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    setLoading(true)

    fetchChart(symbol, preset)
      .then((data) => {
        if (cancelled) return
        setCandles(data.candles)
        setPositive(data.change_pct >= 0)
        onData?.(data)
        setLoading(false)
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [symbol, preset, enabled])

  if (loading) {
    return (
      <div className="chart-loading" style={{ height }}>
        <div className="chart-loading-bar" />
      </div>
    )
  }

  return <TradingChart candles={candles} height={height} mode={mode} positive={positive} />
}
