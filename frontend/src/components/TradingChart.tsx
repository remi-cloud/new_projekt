import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ColorType,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  createChart,
  UTCTimestamp,
} from 'lightweight-charts'
import { fetchChart, fetchPaperPosition, fetchPaperTrades } from '../api'
import { useDashboardContext } from '../context/DashboardContext'
import { PaperTrade } from '../types'
import { ChartPreset, ChartCandle, ChartResponse, INTRADAY_CHART_PRESETS } from '../types/chart'
import { cycleMarkersToChartMarkers, positionOpenMarker, tradesToChartMarkers } from '../utils/chartMarkers'
import { computeRsiSeries } from '../utils/chartIndicators'
import { drawRsiSmear } from '../utils/chartRsiOverlay'
import type { SeriesMarker, Time } from 'lightweight-charts'

interface TradingChartProps {
  candles: ChartCandle[]
  preset?: ChartPreset
  height?: number
  mode?: 'area' | 'candle'
  positive?: boolean
  tradeMarkers?: SeriesMarker<Time>[]
  showRsiShadow?: boolean
  dataReady?: boolean
}

type PriceSeries = ISeriesApi<'Candlestick'> | ISeriesApi<'Area'>

function scheduleOverlay(fn: () => void) {
  requestAnimationFrame(() => requestAnimationFrame(fn))
}

export function TradingChart({
  candles,
  preset = '3M',
  height = 140,
  mode = 'area',
  positive = true,
  tradeMarkers = [],
  showRsiShadow = false,
  dataReady = true,
}: TradingChartProps) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRef = useRef<PriceSeries | null>(null)
  const drawOverlayRef = useRef<(() => void) | null>(null)
  const userZoomedRef = useRef(false)
  const programmaticRef = useRef(false)
  const presetRef = useRef(preset)

  const rsiActive = showRsiShadow && height >= 200
  const headerH = rsiActive ? 32 : 0
  const chartHeight = height - headerH

  const rsiData = useMemo(
    () => (rsiActive && dataReady ? computeRsiSeries(candles) : null),
    [candles, rsiActive, dataReady],
  )

  const sortedMarkers = useMemo(() => {
    const sorted = [...tradeMarkers]
    sorted.sort((a, b) => (a.time as number) - (b.time as number))
    return sorted
  }, [tradeMarkers])

  const runProgrammatic = useCallback((fn: () => void) => {
    programmaticRef.current = true
    fn()
    requestAnimationFrame(() => {
      programmaticRef.current = false
    })
  }, [])

  const drawRsiOverlay = useCallback(() => {
    const chart = chartRef.current
    const canvas = overlayRef.current
    const wrap = wrapRef.current
    if (!chart || !canvas || !wrap || !rsiActive || !rsiData?.points.length) {
      if (canvas) {
        const ctx = canvas.getContext('2d')
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
      }
      return
    }

    const w = wrap.clientWidth
    const h = chartHeight
    if (w < 10 || h < 10) return

    const priceScaleW = chart.priceScale('right').width()
    const plotW = Math.max(w - priceScaleW, Math.floor(w * 0.88))

    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.floor(plotW * dpr)
    canvas.height = Math.floor(h * dpr)
    canvas.style.left = '0'
    canvas.style.top = '0'
    canvas.style.width = `${plotW}px`
    canvas.style.height = `${h}px`

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    drawRsiSmear(ctx, plotW, h, rsiData.points, (time) => chart.timeScale().timeToCoordinate(time))
  }, [chartHeight, rsiActive, rsiData])

  useEffect(() => {
    drawOverlayRef.current = drawRsiOverlay
  }, [drawRsiOverlay])

  const replacePriceSeries = useCallback(() => {
    const chart = chartRef.current
    if (!chart) return

    if (priceSeriesRef.current) {
      chart.removeSeries(priceSeriesRef.current)
      priceSeriesRef.current = null
    }

    const upColor = '#32d74b'
    const downColor = '#ff453a'
    const lineColor = positive ? upColor : downColor

    if (mode === 'candle') {
      priceSeriesRef.current = chart.addCandlestickSeries({
        upColor,
        downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor,
      })
    } else {
      priceSeriesRef.current = chart.addAreaSeries({
        lineColor,
        topColor: positive ? 'rgba(50,215,75,0.28)' : 'rgba(255,69,58,0.28)',
        bottomColor: positive ? 'rgba(50,215,75,0.02)' : 'rgba(255,69,58,0.02)',
        lineWidth: 2,
      })
    }
  }, [mode, positive])

  const applyCandleData = useCallback(() => {
    const chart = chartRef.current
    const series = priceSeriesRef.current
    if (!chart || !series || !candles.length || !dataReady) return

    const presetChanged = presetRef.current !== preset
    if (presetChanged) {
      presetRef.current = preset
      userZoomedRef.current = false
    }

    const savedRange = userZoomedRef.current ? chart.timeScale().getVisibleLogicalRange() : null

    if (mode === 'candle') {
      ;(series as ISeriesApi<'Candlestick'>).setData(
        candles.map((c) => ({
          time: c.time as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      )
    } else {
      ;(series as ISeriesApi<'Area'>).setData(
        candles.map((c) => ({ time: c.time as UTCTimestamp, value: c.close })),
      )
    }

    series.setMarkers(sortedMarkers)

    if (presetChanged || !userZoomedRef.current) {
      runProgrammatic(() => chart.timeScale().fitContent())
    } else if (savedRange) {
      runProgrammatic(() => chart.timeScale().setVisibleLogicalRange(savedRange))
    }

    scheduleOverlay(drawRsiOverlay)
  }, [candles, mode, preset, sortedMarkers, dataReady, runProgrammatic, drawRsiOverlay])

  const fitChart = useCallback(() => {
    const chart = chartRef.current
    if (!chart) return
    runProgrammatic(() => {
      chart.timeScale().fitContent()
      userZoomedRef.current = false
    })
    scheduleOverlay(drawRsiOverlay)
  }, [runProgrammatic, drawRsiOverlay])

  const zoomIn = useCallback(() => {
    const ts = chartRef.current?.timeScale()
    if (!ts) return
    userZoomedRef.current = true
    ts.applyOptions({ barSpacing: Math.min((ts.options().barSpacing ?? 6) + 2, 40) })
    scheduleOverlay(drawRsiOverlay)
  }, [drawRsiOverlay])

  const zoomOut = useCallback(() => {
    const ts = chartRef.current?.timeScale()
    if (!ts) return
    userZoomedRef.current = true
    ts.applyOptions({ barSpacing: Math.max((ts.options().barSpacing ?? 6) - 2, 2) })
    scheduleOverlay(drawRsiOverlay)
  }, [drawRsiOverlay])

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      height: chartHeight,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#6e6e73',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.06)' },
        horzLines: { color: 'rgba(255,255,255,0.06)' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      leftPriceScale: {
        visible: false,
        borderColor: 'rgba(255,255,255,0.08)',
        scaleMargins: { top: 0.04, bottom: 0.04 },
        autoScale: false,
        minimumWidth: 0,
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.1)',
        scaleMargins: { top: 0.06, bottom: 0.06 },
        autoScale: true,
        minimumWidth: 56,
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.1)',
        timeVisible: mode === 'candle',
        secondsVisible: preset === '1m',
        rightOffset: 4,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true, axisDoubleClickReset: false },
    })
    chartRef.current = chart

    replacePriceSeries()

    chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
      if (programmaticRef.current) return
      userZoomedRef.current = true
      drawOverlayRef.current?.()
    })

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
      drawOverlayRef.current?.()
    })
    ro.observe(containerRef.current)
    if (wrapRef.current) ro.observe(wrapRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
      priceSeriesRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    chartRef.current?.applyOptions({
      height: chartHeight,
      timeScale: {
        timeVisible: mode === 'candle',
        secondsVisible: preset === '1m',
      },
    })
    scheduleOverlay(drawRsiOverlay)
  }, [chartHeight, mode, preset, drawRsiOverlay])

  useEffect(() => {
    scheduleOverlay(drawRsiOverlay)
  }, [rsiData, drawRsiOverlay])

  useEffect(() => {
    if (!chartRef.current) return
    replacePriceSeries()
    applyCandleData()
  }, [mode, positive, replacePriceSeries, applyCandleData])

  useEffect(() => {
    applyCandleData()
  }, [applyCandleData])

  if (!dataReady || !candles.length) {
    return <div className="chart-empty" style={{ height }}>Brak danych wykresu</div>
  }

  return (
    <div className="chart-stack">
      <div className="chart-pane chart-pane-price">
        {rsiActive && (
          <div className="chart-pane-header">
            <span className="pane-label">
              Cena · {preset}
              {rsiData?.latest != null && (
                <span
                  className={`pane-rsi-hint${
                    rsiData.latest <= 30 ? ' rsi-oversold' : rsiData.latest >= 70 ? ' rsi-overbought' : ''
                  }`}
                >
                  {' '}
                  · RSI {rsiData.latest.toFixed(0)}
                </span>
              )}
            </span>
            <div className="chart-zoom-controls">
              <button type="button" className="chart-zoom-btn tap-target" onClick={zoomOut} title="Oddal">−</button>
              <button type="button" className="chart-zoom-btn tap-target" onClick={fitChart} title="Reset widoku">⟲</button>
              <button type="button" className="chart-zoom-btn tap-target" onClick={zoomIn} title="Przybliż">+</button>
            </div>
          </div>
        )}
        <div className="chart-rsi-wrap" ref={wrapRef}>
          <div className="trading-chart" ref={containerRef} style={{ height: chartHeight }} />
          {rsiActive && (
            <canvas ref={overlayRef} className="chart-rsi-overlay" aria-hidden />
          )}
          {rsiActive && (
            <div className="chart-rsi-scale" aria-hidden>
              <div className="chart-rsi-scale-zone chart-rsi-scale-hot">
                <span className="rsi-label-hot">100</span>
                <span className="rsi-label-hot">70</span>
                <span className="rsi-zone-tag">wykupienie</span>
              </div>
              <div className="chart-rsi-scale-zone chart-rsi-scale-neutral">
                <span>50</span>
              </div>
              <div className="chart-rsi-scale-zone chart-rsi-scale-cold">
                <span className="rsi-label-cold">30</span>
                <span className="rsi-label-cold">0</span>
                <span className="rsi-zone-tag">wyprzedanie</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ChartLoaderProps {
  symbol: string
  preset?: ChartPreset
  height?: number
  mode?: 'area' | 'candle'
  enabled?: boolean
  onData?: (data: ChartResponse) => void
  tradesRevision?: number
  showRsiShadow?: boolean
}

export function ChartLoader({
  symbol,
  preset = '3M',
  height = 140,
  mode = 'area',
  enabled = true,
  onData,
  tradesRevision = 0,
  showRsiShadow = false,
}: ChartLoaderProps) {
  const { lastEventAt } = useDashboardContext()
  const [chartBundle, setChartBundle] = useState<{
    candles: ChartCandle[]
    preset: ChartPreset
    positive: boolean
    cycleMarkers: ChartResponse['cycle_markers']
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [trades, setTrades] = useState<PaperTrade[]>([])
  const [positionOpenedAt, setPositionOpenedAt] = useState<string | null>(null)
  const loadGenRef = useRef(0)
  const activePresetRef = useRef<ChartPreset>(preset)

  const loadChart = useCallback(
    async (requestedPreset: ChartPreset, opts?: { silent?: boolean }) => {
      if (!enabled) return
      const silent = opts?.silent ?? false
      const gen = ++loadGenRef.current

      if (!silent) setLoading(true)
      setLoadError(null)

      try {
        const data = await fetchChart(symbol, requestedPreset)
        if (gen !== loadGenRef.current) return
        if (!data.candles?.length) {
          setChartBundle(null)
          setLoadError(`Brak świec dla interwału ${requestedPreset}`)
          return
        }
        setChartBundle({
          candles: data.candles,
          preset: requestedPreset,
          positive: data.change_pct >= 0,
          cycleMarkers: data.cycle_markers ?? [],
        })
        activePresetRef.current = requestedPreset
        onData?.(data)
      } catch {
        if (gen !== loadGenRef.current) return
        if (!silent) {
          await new Promise((r) => setTimeout(r, 2000))
          if (gen !== loadGenRef.current) return
          try {
            const data = await fetchChart(symbol, requestedPreset)
            if (gen !== loadGenRef.current) return
            if (!data.candles?.length) {
              setChartBundle(null)
              setLoadError(`Brak świec dla interwału ${requestedPreset}`)
              return
            }
            setChartBundle({
              candles: data.candles,
              preset: requestedPreset,
              positive: data.change_pct >= 0,
              cycleMarkers: data.cycle_markers ?? [],
            })
            activePresetRef.current = requestedPreset
            onData?.(data)
          } catch {
            if (gen === loadGenRef.current) {
              setChartBundle(null)
              setLoadError(`Nie udało się załadować ${requestedPreset}`)
            }
          }
        } else if (gen === loadGenRef.current) {
          setLoadError(`Odświeżenie ${requestedPreset} nieudane`)
        }
      } finally {
        if (gen === loadGenRef.current && !silent) setLoading(false)
      }
    },
    [enabled, symbol, onData],
  )

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
    return () => { cancelled = true }
  }, [symbol, enabled, tradesRevision])

  useEffect(() => {
    if (!enabled) return
    activePresetRef.current = preset
    setChartBundle(null)
    setLoadError(null)
    void loadChart(preset)
  }, [enabled, symbol, preset, loadChart])

  useEffect(() => {
    if (!enabled || !lastEventAt) return
    void loadChart(activePresetRef.current, { silent: true })
  }, [lastEventAt, enabled, loadChart])

  const PRICE_REFRESH_MS = INTRADAY_CHART_PRESETS.includes(preset) ? 30_000 : 60_000

  useEffect(() => {
    if (!enabled) return
    const id = setInterval(
      () => void loadChart(activePresetRef.current, { silent: true }),
      PRICE_REFRESH_MS,
    )
    return () => clearInterval(id)
  }, [enabled, symbol, preset, loadChart, PRICE_REFRESH_MS])

  const dataReady = chartBundle !== null && chartBundle.preset === preset && !loading
  const displayCandles = dataReady ? chartBundle.candles : []
  const displayPositive = chartBundle?.positive ?? true

  if (loading && !chartBundle) {
    return (
      <div className="chart-loading" style={{ height }}>
        <div className="chart-loading-bar" />
        <span className="chart-loading-label">Ładowanie {preset}…</span>
      </div>
    )
  }

  if (loadError && !chartBundle) {
    return (
      <div className="chart-empty chart-empty-error" style={{ height }}>
        <span>{loadError}</span>
        <button type="button" className="chart-retry-btn tap-target" onClick={() => void loadChart(preset)}>
          Spróbuj ponownie
        </button>
      </div>
    )
  }

  const tradeMarkers = [
    ...cycleMarkersToChartMarkers(chartBundle?.cycleMarkers ?? [], displayCandles),
    ...tradesToChartMarkers(trades, displayCandles),
    ...(positionOpenedAt ? positionOpenMarker(positionOpenedAt, displayCandles) : []),
  ]

  return (
    <div className={`chart-loader-wrap${loading ? ' chart-loader-loading' : ''}`}>
      {loading && chartBundle && <div className="chart-loader-overlay" />}
      <TradingChart
        candles={displayCandles}
        preset={preset}
        height={height}
        mode={mode}
        positive={displayPositive}
        tradeMarkers={tradeMarkers}
        showRsiShadow={showRsiShadow}
        dataReady={dataReady}
      />
    </div>
  )
}
