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

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return

    const chart = createChart(el, {
      height,
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

    const ro = new ResizeObserver(() => {
      if (wrapRef.current) chart.applyOptions({ width: wrapRef.current.clientWidth })
    })
    ro.observe(el)
    chart.applyOptions({ width: el.clientWidth })

    return () => {
      ro.disconnect()
      chart.remove()
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
    equityRef.current.setData(equity.map((p) => ({ time: p.time as UTCTimestamp, value: p.equity })))
    optRef.current?.setData((optimistic ?? []).map((p) => ({ time: p.time as UTCTimestamp, value: p.equity })))
    pesRef.current?.setData((pessimistic ?? []).map((p) => ({ time: p.time as UTCTimestamp, value: p.equity })))
    bhRef.current?.setData((buyHold ?? []).map((p) => ({ time: p.time as UTCTimestamp, value: p.equity })))
    priceRef.current?.setData((price ?? []).map((p) => ({ time: p.time as UTCTimestamp, value: p.value })))
    chartRef.current?.timeScale().fitContent()
  }, [equity, buyHold, optimistic, pessimistic, price])

  return <div ref={wrapRef} className="roi-chart" style={{ height }} />
}
