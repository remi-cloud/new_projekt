import { useEffect, useRef, useState } from 'react'
import {
  ColorType,
  CrosshairMode,
  createChart,
  UTCTimestamp,
} from 'lightweight-charts'
import { fetchChart, fetchPaperPosition, fetchPaperTrades } from '../api'
import { PaperTrade } from '../types'
import { positionOpenMarker, tradesToChartMarkers } from '../utils/chartMarkers'
import { ChartCandle, ChartPreset, ChartResponse } from '../types/chart'
import type { SeriesMarker, Time } from 'lightweight-charts'

interface TradingChartProps {
  candles: ChartCandle[]
  height?: number
  mode?: 'area' | 'candle'
  positive?: boolean
  tradeMarkers?: SeriesMarker<Time>[]
}

export function TradingChart({
  candles,
  height = 140,
  mode = 'area',
  positive = true,
  tradeMarkers = [],
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
      if (tradeMarkers.length) {
        series.setMarkers(tradeMarkers)
      }
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
      if (tradeMarkers.length) {
        series.setMarkers(tradeMarkers)
      }
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
  }, [candles, height, mode, positive, tradeMarkers])

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
  tradesRevision?: number
}

export function ChartLoader({
  symbol,
  preset = '3M',
  height = 140,
  mode = 'area',
  enabled = true,
  onData,
  tradesRevision = 0,
}: ChartLoaderProps) {
  const [candles, setCandles] = useState<ChartCandle[]>([])
  const [loading, setLoading] = useState(false)
  const [positive, setPositive] = useState(true)
  const [trades, setTrades] = useState<PaperTrade[]>([])
  const [positionOpenedAt, setPositionOpenedAt] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    Promise.all([fetchPaperTrades(symbol), fetchPaperPosition(symbol)])
      .then(([tradeData, position]) => {
        if (cancelled) return
        setTrades(tradeData)
        setPositionOpenedAt(position?.opened_at ?? null)
      })
      .catch(() => {
        if (!cancelled) {
          setTrades([])
          setPositionOpenedAt(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [symbol, enabled, tradesRevision])

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
        if (cancelled) return
        // Retry once — charts often fail when server is busy scanning.
        setTimeout(() => {
          if (cancelled) return
          fetchChart(symbol, preset)
            .then((data) => {
              if (cancelled) return
              setCandles(data.candles)
              setPositive(data.change_pct >= 0)
              onData?.(data)
            })
            .catch(() => {})
            .finally(() => {
              if (!cancelled) setLoading(false)
            })
        }, 2000)
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

  const tradeMarkers = [
    ...tradesToChartMarkers(trades, candles),
    ...(positionOpenedAt ? positionOpenMarker(positionOpenedAt, candles) : []),
  ]

  return (
    <TradingChart
      candles={candles}
      height={height}
      mode={mode}
      positive={positive}
      tradeMarkers={tradeMarkers}
    />
  )
}
