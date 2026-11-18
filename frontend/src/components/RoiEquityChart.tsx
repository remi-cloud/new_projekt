import { useEffect, useRef } from 'react'
import { ColorType, IChartApi, ISeriesApi, createChart, UTCTimestamp } from 'lightweight-charts'

export type RoiCurvePoint = { time: number; equity: number }
export type RoiPricePoint = { time: number; value: number }

type Props = {
  equity: RoiCurvePoint[]
  buyHold?: RoiCurvePoint[] | null
  optimistic?: RoiCurvePoint[] | null
  pessimistic?: RoiCurvePoint[] | null
  price?: RoiPricePoint[] | null
  height?: number
}

export function RoiEquityChart({
  equity,
  buyHold,
  optimistic,
  pessimistic,
  price,
  height = 320,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const equityRef = useRef<ISeriesApi<'Area'> | null>(null)
  const bhRef = useRef<ISeriesApi<'Line'> | null>(null)
  const optRef = useRef<ISeriesApi<'Line'> | null>(null)
  const pesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const priceRef = useRef<ISeriesApi<'Line'> | null>(null)
  const dataRef = useRef({ equity, buyHold, optimistic, pessimistic, price })
  dataRef.current = { equity, buyHold, optimistic, pessimistic, price }

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    let chart: IChartApi | null = null
    const mount = () => {
      if (chart || el.clientWidth < 2) return
      try {
        chart = createChart(el, {
          height,
          width: el.clientWidth,
          layout: {
            background: { type: ColorType.Solid, color: 'transparent' },
            textColor: 'rgba(200, 200, 210, 0.75)',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
          },
          grid: {
            vertLines: { color: 'rgba(255,255,255,0.04)' },
            horzLines: { color: 'rgba(255,255,255,0.04)' },
          },
          rightPriceScale: { borderVisible: false },
          timeScale: { borderVisible: false, timeVisible: true },
          crosshair: { mode: 1 },
        })
        chartRef.current = chart
        equityRef.current = chart.addAreaSeries({
          lineColor: '#d4af37',
          topColor: 'rgba(212, 175, 55, 0.35)',
          bottomColor: 'rgba(212, 175, 55, 0.02)',
          lineWidth: 2,
          priceLineVisible: false,
        })
        optRef.current = chart.addLineSeries({
          color: 'rgba(52, 211, 153, 0.7)',
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
        })
        pesRef.current = chart.addLineSeries({
          color: 'rgba(248, 113, 113, 0.65)',
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
        })
        bhRef.current = chart.addLineSeries({
          color: 'rgba(148, 163, 184, 0.85)',
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
        })
        priceRef.current = chart.addLineSeries({
          color: 'rgba(96, 165, 250, 0.55)',
          lineWidth: 1,
          priceScaleId: 'price',
          priceLineVisible: false,
        })
        chart.priceScale('price').applyOptions({
          scaleMargins: { top: 0.72, bottom: 0 },
          visible: false,
        })
      } catch {
        chart = null
      }
    }
    mount()
    const applyNow = () => {
      const chartNow = chartRef.current
      if (!chartNow || !equityRef.current) return
      const current = dataRef.current
      const points = (rows: RoiCurvePoint[]) => {
        const seen = new Set<number>()
        return rows
          .filter((p) => Number.isFinite(p.time) && Number.isFinite(p.equity))
          .sort((a, b) => a.time - b.time)
          .filter((p) => (seen.has(p.time) ? false : (seen.add(p.time), true)))
          .map((p) => ({ time: p.time as UTCTimestamp, value: p.equity }))
      }
      const put = (series: { setData: (data: { time: UTCTimestamp; value: number }[]) => void } | null, data: { time: UTCTimestamp; value: number }[]) => {
        if (!series || data.length < 2) return
        try { series.setData(data) } catch { /* narrow frame */ }
      }
      put(equityRef.current, points(current.equity))
      put(optRef.current, points(current.optimistic ?? []))
      put(pesRef.current, points(current.pessimistic ?? []))
      put(bhRef.current, points(current.buyHold ?? []))
    }
    applyNow()
    const ro = new ResizeObserver(() => {
      try {
        if (!chart) {
          mount()
          applyNow()
        } else if (el.clientWidth > 1) chart.applyOptions({ width: el.clientWidth })
      } catch {
        /* The scale can be null for one frame on a narrow phone. */
      }
    })
    ro.observe(el)
    return () => {
      ro.disconnect()
      try { chart?.remove() } catch { /* already gone */ }
      chartRef.current = null
      equityRef.current = null
      bhRef.current = null
      optRef.current = null
      pesRef.current = null
      priceRef.current = null
    }
  }, [height])

  useEffect(() => {
    if (!equityRef.current || !equity.length) return
    const points = (rows: RoiCurvePoint[]) => {
      const seen = new Set<number>()
      return rows
        .filter((p) => Number.isFinite(p.time) && Number.isFinite(p.equity))
        .sort((a, b) => a.time - b.time)
        .filter((p) => (seen.has(p.time) ? false : (seen.add(p.time), true)))
        .map((p) => ({ time: p.time as UTCTimestamp, value: p.equity }))
    }
    const put = (series: { setData: (data: { time: UTCTimestamp; value: number }[]) => void } | null, data: { time: UTCTimestamp; value: number }[]) => {
      if (!series || data.length < 2) return
      series.setData(data)
    }
    try {
      put(equityRef.current, points(equity))
      put(optRef.current, points(optimistic ?? []))
      put(pesRef.current, points(pessimistic ?? []))
      put(bhRef.current, points(buyHold ?? []))
      const pricePoints = (price ?? [])
        .filter((p) => Number.isFinite(p.time) && Number.isFinite(p.value))
        .map((p) => ({ time: p.time as UTCTimestamp, value: p.value }))
      if (priceRef.current && pricePoints.length >= 2) priceRef.current.setData(pricePoints)
    } catch {
      /* Mobile layout can report a zero-width scale before the first paint. */
    }
  }, [equity, buyHold, optimistic, pessimistic, price])

  return <div ref={wrapRef} className="roi-chart" style={{ height }} />
}
