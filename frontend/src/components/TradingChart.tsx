import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react'
import {
  ColorType,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  LineStyle,
  createChart,
  UTCTimestamp,
} from 'lightweight-charts'
import { fetchChart, fetchPaperPosition, fetchPaperTrades } from '../api'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { PaperTrade } from '../types'
import { ChartPreset, ChartCandle, ChartResponse, INTRADAY_CHART_PRESETS, canZoomChartIn, canZoomChartOut, stepChartPreset } from '../types/chart'
import { cycleMarkersToChartMarkers, positionOpenMarker, tradesToChartMarkers } from '../utils/chartMarkers'
import {
  ChartIndicatorFlags,
  computeAtrSeries,
  computeBollingerSeries,
  computeEmaSeries,
  computeMacdSeries,
  computeRsiSeries,
  computeSmaSeries,
  computeVolumeSeries,
  latestValue,
} from '../utils/chartIndicators'
import { drawRsiSmear } from '../utils/chartRsiOverlay'
import type { SeriesMarker, Time } from 'lightweight-charts'

interface TradingChartProps {
  candles: ChartCandle[]
  preset?: ChartPreset
  height?: number
  mode?: 'area' | 'candle'
  positive?: boolean
  tradeMarkers?: SeriesMarker<Time>[]
  /** @deprecated use indicators.rsi */
  showRsiShadow?: boolean
  indicators?: ChartIndicatorFlags
  dataReady?: boolean
  /** Zoom +/− steps time preset (shorter / longer). */
  onPresetStep?: (next: ChartPreset) => void
  /** Target preset for reset (⟲). Defaults to current preset if omitted. */
  resetPreset?: ChartPreset
}

type PriceSeries = ISeriesApi<'Candlestick'> | ISeriesApi<'Area'>

function scheduleOverlay(fn: () => void) {
  requestAnimationFrame(() => requestAnimationFrame(fn))
}

function mergeIndicators(
  flags: ChartIndicatorFlags | undefined,
  showRsiShadow: boolean,
): Required<ChartIndicatorFlags> {
  return {
    rsi: flags?.rsi ?? showRsiShadow,
    sma: flags?.sma ?? false,
    ema: flags?.ema ?? false,
    bb: flags?.bb ?? false,
    volume: flags?.volume ?? false,
    macd: flags?.macd ?? false,
    atr: flags?.atr ?? false,
  }
}

export function TradingChart({
  candles,
  preset = '3M',
  height = 140,
  mode = 'area',
  positive = true,
  tradeMarkers = [],
  showRsiShadow = false,
  indicators,
  dataReady = true,
  onPresetStep,
  resetPreset,
}: TradingChartProps) {
  const { t } = useLocale()
  const wrapRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const priceSeriesRef = useRef<PriceSeries | null>(null)
  const sma20Ref = useRef<ISeriesApi<'Line'> | null>(null)
  const sma50Ref = useRef<ISeriesApi<'Line'> | null>(null)
  const ema20Ref = useRef<ISeriesApi<'Line'> | null>(null)
  const ema50Ref = useRef<ISeriesApi<'Line'> | null>(null)
  const bbUpperRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbMidRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbLowerRef = useRef<ISeriesApi<'Line'> | null>(null)
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const macdLineRef = useRef<ISeriesApi<'Line'> | null>(null)
  const macdSignalRef = useRef<ISeriesApi<'Line'> | null>(null)
  const macdHistRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const drawOverlayRef = useRef<(() => void) | null>(null)
  const userZoomedRef = useRef(false)
  const programmaticRef = useRef(false)
  const presetRef = useRef(preset)

  const ind = useMemo(() => mergeIndicators(indicators, showRsiShadow), [indicators, showRsiShadow])
  const deskActive = height >= 200
  const rsiActive = deskActive && ind.rsi
  const headerH = deskActive ? 32 : 0
  const chartHeight = height - headerH

  const rsiData = useMemo(
    () => (rsiActive && dataReady ? computeRsiSeries(candles) : null),
    [candles, rsiActive, dataReady],
  )
  const atrLatest = useMemo(() => {
    if (!deskActive || !ind.atr || !dataReady) return null
    return latestValue(computeAtrSeries(candles))
  }, [candles, deskActive, ind.atr, dataReady])
  const macdLatest = useMemo(() => {
    if (!deskActive || !ind.macd || !dataReady) return null
    return computeMacdSeries(candles).latest
  }, [candles, deskActive, ind.macd, dataReady])

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

  const applyPriceScaleMargins = useCallback((chart: IChartApi) => {
    const hasVol = Boolean(volumeRef.current)
    const hasMacd = Boolean(macdHistRef.current || macdLineRef.current)
    let bottom = 0.06
    if (hasVol && hasMacd) bottom = 0.38
    else if (hasMacd) bottom = 0.28
    else if (hasVol) bottom = 0.22
    chart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.06, bottom },
    })
    if (hasVol) {
      chart.priceScale('vol').applyOptions({
        scaleMargins: { top: hasMacd ? 0.78 : 0.82, bottom: hasMacd ? 0.14 : 0 },
      })
    }
    if (hasMacd) {
      chart.priceScale('macd').applyOptions({
        scaleMargins: { top: 0.72, bottom: 0 },
      })
    }
  }, [])

  const removeSeries = useCallback((ref: MutableRefObject<ISeriesApi<'Line'> | ISeriesApi<'Histogram'> | null>) => {
    const chart = chartRef.current
    if (chart && ref.current) {
      try {
        chart.removeSeries(ref.current)
      } catch {
        /* already removed with chart */
      }
    }
    ref.current = null
  }, [])

  const syncIndicatorSeries = useCallback(() => {
    const chart = chartRef.current
    if (!chart || !dataReady || !candles.length) return

    const ensureLine = (
      ref: MutableRefObject<ISeriesApi<'Line'> | null>,
      opts: Parameters<IChartApi['addLineSeries']>[0],
    ) => {
      if (!ref.current) ref.current = chart.addLineSeries(opts)
      return ref.current
    }
    const ensureHist = (
      ref: MutableRefObject<ISeriesApi<'Histogram'> | null>,
      opts: Parameters<IChartApi['addHistogramSeries']>[0],
    ) => {
      if (!ref.current) ref.current = chart.addHistogramSeries(opts)
      return ref.current
    }

    if (deskActive && ind.sma) {
      ensureLine(sma20Ref, {
        color: '#f59e0b',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(computeSmaSeries(candles, 20))
      ensureLine(sma50Ref, {
        color: '#a78bfa',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(computeSmaSeries(candles, 50))
    } else {
      removeSeries(sma20Ref)
      removeSeries(sma50Ref)
    }

    if (deskActive && ind.ema) {
      ensureLine(ema20Ref, {
        color: '#38bdf8',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(computeEmaSeries(candles, 20))
      ensureLine(ema50Ref, {
        color: '#e879f9',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(computeEmaSeries(candles, 50))
    } else {
      removeSeries(ema20Ref)
      removeSeries(ema50Ref)
    }

    if (deskActive && ind.bb) {
      const bb = computeBollingerSeries(candles, 20, 2)
      ensureLine(bbUpperRef, {
        color: 'rgba(148, 163, 184, 0.7)',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(bb.map((p) => ({ time: p.time, value: p.upper })))
      ensureLine(bbMidRef, {
        color: 'rgba(100, 116, 139, 0.9)',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(bb.map((p) => ({ time: p.time, value: p.mid })))
      ensureLine(bbLowerRef, {
        color: 'rgba(148, 163, 184, 0.7)',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(bb.map((p) => ({ time: p.time, value: p.lower })))
    } else {
      removeSeries(bbUpperRef)
      removeSeries(bbMidRef)
      removeSeries(bbLowerRef)
    }

    if (deskActive && ind.volume) {
      ensureHist(volumeRef, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
        lastValueVisible: false,
        priceLineVisible: false,
      }).setData(computeVolumeSeries(candles))
    } else {
      removeSeries(volumeRef)
    }

    if (deskActive && ind.macd) {
      const macd = computeMacdSeries(candles)
      ensureHist(macdHistRef, {
        priceScaleId: 'macd',
        lastValueVisible: false,
        priceLineVisible: false,
      }).setData(
        macd.points.map((p) => ({
          time: p.time,
          value: p.hist,
          color: p.hist >= 0 ? 'rgba(50, 215, 75, 0.45)' : 'rgba(255, 69, 58, 0.45)',
        })),
      )
      ensureLine(macdLineRef, {
        color: '#60a5fa',
        lineWidth: 1,
        priceScaleId: 'macd',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(macd.points.map((p) => ({ time: p.time, value: p.macd })))
      ensureLine(macdSignalRef, {
        color: '#f472b6',
        lineWidth: 1,
        priceScaleId: 'macd',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }).setData(macd.points.map((p) => ({ time: p.time, value: p.signal })))
    } else {
      removeSeries(macdHistRef)
      removeSeries(macdLineRef)
      removeSeries(macdSignalRef)
    }

    applyPriceScaleMargins(chart)
  }, [applyPriceScaleMargins, candles, dataReady, deskActive, ind, removeSeries])

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
    syncIndicatorSeries()

    if (presetChanged || !userZoomedRef.current) {
      runProgrammatic(() => chart.timeScale().fitContent())
    } else if (savedRange) {
      runProgrammatic(() => chart.timeScale().setVisibleLogicalRange(savedRange))
    }

    scheduleOverlay(drawRsiOverlay)
  }, [
    candles,
    mode,
    preset,
    sortedMarkers,
    dataReady,
    runProgrammatic,
    drawRsiOverlay,
    syncIndicatorSeries,
  ])

  const fitChart = useCallback(() => {
    const target = resetPreset ?? preset
    if (onPresetStep && target !== preset) {
      onPresetStep(target)
      return
    }
    const chart = chartRef.current
    if (!chart) return
    runProgrammatic(() => {
      chart.timeScale().fitContent()
      userZoomedRef.current = false
    })
    scheduleOverlay(drawRsiOverlay)
  }, [runProgrammatic, drawRsiOverlay, onPresetStep, resetPreset, preset])

  const zoomIn = useCallback(() => {
    if (!onPresetStep || !canZoomChartIn(preset)) return
    onPresetStep(stepChartPreset(preset, -1))
  }, [onPresetStep, preset])

  const zoomOut = useCallback(() => {
    if (!onPresetStep || !canZoomChartOut(preset)) return
    onPresetStep(stepChartPreset(preset, 1))
  }, [onPresetStep, preset])

  const canIn = Boolean(onPresetStep) && canZoomChartIn(preset)
  const canOut = Boolean(onPresetStep) && canZoomChartOut(preset)

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
      sma20Ref.current = null
      sma50Ref.current = null
      ema20Ref.current = null
      ema50Ref.current = null
      bbUpperRef.current = null
      bbMidRef.current = null
      bbLowerRef.current = null
      volumeRef.current = null
      macdLineRef.current = null
      macdSignalRef.current = null
      macdHistRef.current = null
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

  useEffect(() => {
    syncIndicatorSeries()
    scheduleOverlay(drawRsiOverlay)
  }, [syncIndicatorSeries, drawRsiOverlay])

  if (!dataReady || !candles.length) {
    return <div className="chart-empty" style={{ height }}>{t('chart.noData')}</div>
  }

  const hintBits: string[] = []
  if (rsiData?.latest != null) hintBits.push(t('chart.rsi', { n: rsiData.latest.toFixed(0) }))
  if (atrLatest != null) hintBits.push(t('chart.atr', { n: atrLatest.toPrecision(4) }))
  if (macdLatest) hintBits.push(t('chart.macdHint', { n: macdLatest.hist.toPrecision(3) }))

  return (
    <div className="chart-stack">
      <div className="chart-pane chart-pane-price">
        {deskActive && (
          <div className="chart-pane-header">
            <span className="pane-label">
              {t('chart.pricePreset', { preset })}
              {hintBits.length > 0 && (
                <span className="pane-rsi-hint">
                  {' '}
                  · {hintBits.join(' · ')}
                </span>
              )}
            </span>
            <div className="chart-zoom-controls">
              <button
                type="button"
                className="chart-zoom-btn tap-target"
                onClick={zoomOut}
                title={t('chart.zoomOut')}
                disabled={!canOut}
                aria-disabled={!canOut}
              >
                −
              </button>
              <button type="button" className="chart-zoom-btn tap-target" onClick={fitChart} title={t('chart.resetView')}>
                ⟲
              </button>
              <button
                type="button"
                className="chart-zoom-btn tap-target"
                onClick={zoomIn}
                title={t('chart.zoomIn')}
                disabled={!canIn}
                aria-disabled={!canIn}
              >
                +
              </button>
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
                <span className="rsi-zone-tag">{t('chart.overbought')}</span>
              </div>
              <div className="chart-rsi-scale-zone chart-rsi-scale-neutral">
                <span>50</span>
              </div>
              <div className="chart-rsi-scale-zone chart-rsi-scale-cold">
                <span className="rsi-label-cold">30</span>
                <span className="rsi-label-cold">0</span>
                <span className="rsi-zone-tag">{t('chart.oversold')}</span>
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
  indicators?: ChartIndicatorFlags
  /** Notify parent when zoom +/− / reset changes time preset (e.g. InstrumentPanel TF chips). */
  onPresetChange?: (preset: ChartPreset) => void
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
  indicators,
  onPresetChange,
}: ChartLoaderProps) {
  const { t } = useLocale()
  const { lastEventAt } = useDashboardContext()
  const [activePreset, setActivePreset] = useState<ChartPreset>(preset)
  const resetPresetRef = useRef<ChartPreset>(preset)
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
  const steppingRef = useRef(false)

  // Parent TF chip / prop sync (reset target updates only on TF/symbol, not zoom steps)
  useEffect(() => {
    setActivePreset(preset)
    activePresetRef.current = preset
    if (!steppingRef.current) {
      resetPresetRef.current = preset
    }
    steppingRef.current = false
  }, [preset, symbol])

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
          setLoadError(t('chart.noCandles', { preset: requestedPreset }))
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
              setLoadError(t('chart.noCandles', { preset: requestedPreset }))
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
              setLoadError(t('chart.loadFailed', { preset: requestedPreset }))
            }
          }
        } else if (gen === loadGenRef.current) {
          setLoadError(t('chart.refreshFailed', { preset: requestedPreset }))
        }
      } finally {
        if (gen === loadGenRef.current && !silent) setLoading(false)
      }
    },
    [enabled, symbol, onData, t],
  )

  const handlePresetStep = useCallback(
    (next: ChartPreset) => {
      if (next === activePresetRef.current) return
      steppingRef.current = true
      if (onPresetChange) {
        onPresetChange(next)
        return
      }
      setActivePreset(next)
      activePresetRef.current = next
    },
    [onPresetChange],
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
    return () => {
      cancelled = true
    }
  }, [symbol, enabled, tradesRevision])

  useEffect(() => {
    if (!enabled) return
    activePresetRef.current = activePreset
    setChartBundle(null)
    setLoadError(null)
    void loadChart(activePreset)
  }, [enabled, symbol, activePreset, loadChart])

  useEffect(() => {
    if (!enabled || !lastEventAt) return
    void loadChart(activePresetRef.current, { silent: true })
  }, [lastEventAt, enabled, loadChart])

  const PRICE_REFRESH_MS = INTRADAY_CHART_PRESETS.includes(activePreset) ? 30_000 : 60_000

  useEffect(() => {
    if (!enabled) return
    const id = setInterval(
      () => void loadChart(activePresetRef.current, { silent: true }),
      PRICE_REFRESH_MS,
    )
    return () => clearInterval(id)
  }, [enabled, symbol, activePreset, loadChart, PRICE_REFRESH_MS])

  const dataReady = chartBundle !== null && chartBundle.preset === activePreset && !loading
  const displayCandles = dataReady ? chartBundle.candles : []
  const displayPositive = chartBundle?.positive ?? true

  const markerLabels = useMemo(
    () => ({
      cycleEntry: t('markers.wej'),
      cycleExit: t('markers.wyj'),
      shortOngoing: t('markers.shortOngoing'),
      tradeBuy: t('markers.buy'),
      tradeSell: t('markers.sell'),
      positionOpen: t('markers.open'),
    }),
    [t],
  )

  const tradeMarkers = useMemo(
    () => [
      ...cycleMarkersToChartMarkers(chartBundle?.cycleMarkers ?? [], displayCandles, markerLabels),
      ...tradesToChartMarkers(trades, displayCandles, markerLabels),
      ...(positionOpenedAt ? positionOpenMarker(positionOpenedAt, displayCandles, markerLabels) : []),
    ],
    [chartBundle?.cycleMarkers, displayCandles, trades, positionOpenedAt, markerLabels],
  )

  if (loading && !chartBundle) {
    return (
      <div className="chart-loading" style={{ height }}>
        <div className="chart-loading-bar" />
        <span className="chart-loading-label">{t('chart.loadingPreset', { preset: activePreset })}</span>
      </div>
    )
  }

  if (loadError && !chartBundle) {
    return (
      <div className="chart-empty chart-empty-error" style={{ height }}>
        <span>{loadError}</span>
        <button type="button" className="chart-retry-btn tap-target" onClick={() => void loadChart(activePreset)}>
          {t('chart.retry')}
        </button>
      </div>
    )
  }

  return (
    <div className={`chart-loader-wrap${loading ? ' chart-loader-loading' : ''}`}>
      {loading && chartBundle && <div className="chart-loader-overlay" />}
      <TradingChart
        candles={displayCandles}
        preset={activePreset}
        height={height}
        mode={mode}
        positive={displayPositive}
        tradeMarkers={tradeMarkers}
        showRsiShadow={showRsiShadow}
        indicators={indicators}
        dataReady={dataReady}
        onPresetStep={handlePresetStep}
        resetPreset={resetPresetRef.current}
      />
    </div>
  )
}
