import { useEffect, useRef } from 'react'
import { AssetClass, Region } from '../types'
import { presetToTvInterval, toTradingViewSymbol } from '../utils/tradingViewSymbol'

interface TradingViewChartProps {
  symbol: string
  assetClass?: AssetClass
  region?: Region
  height?: number
  interval?: string
}

function loadTradingViewWidget(
  container: HTMLDivElement,
  widgetUrl: string,
  config: Record<string, unknown>,
) {
  container.innerHTML = ''
  const widgetEl = document.createElement('div')
  widgetEl.className = 'tradingview-widget-container__widget'
  widgetEl.style.height = '100%'
  widgetEl.style.width = '100%'
  container.appendChild(widgetEl)

  const script = document.createElement('script')
  script.type = 'text/javascript'
  script.src = widgetUrl
  script.async = true
  script.innerHTML = JSON.stringify(config)
  container.appendChild(script)
}

export function TradingViewChart({
  symbol,
  assetClass,
  region,
  height = 360,
  interval = '1',
}: TradingViewChartProps) {
  const ref = useRef<HTMLDivElement>(null)
  const tvSymbol = toTradingViewSymbol(symbol, assetClass, region)

  useEffect(() => {
    if (!ref.current) return
    loadTradingViewWidget(
      ref.current,
      'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js',
      {
        autosize: true,
        symbol: tvSymbol,
        interval,
        timezone: 'Europe/Warsaw',
        theme: 'dark',
        style: '1',
        locale: 'pl',
        enable_publishing: false,
        allow_symbol_change: false,
        hide_top_toolbar: false,
        hide_legend: false,
        save_image: false,
        calendar: false,
        support_host: 'https://www.tradingview.com',
        backgroundColor: '#000000',
        gridColor: 'rgba(255,255,255,0.06)',
      },
    )
  }, [tvSymbol, interval])

  return (
    <div className="tradingview-wrap" style={{ height, width: '100%' }}>
      <div
        ref={ref}
        className="tradingview-widget-container"
        style={{ height: '100%', width: '100%' }}
      />
    </div>
  )
}

interface TradingViewQuoteProps {
  symbol: string
  assetClass?: AssetClass
  region?: Region
}

/** Live price ticker from TradingView (real-time, extended hours). */
export function TradingViewQuote({ symbol, assetClass, region }: TradingViewQuoteProps) {
  const ref = useRef<HTMLDivElement>(null)
  const tvSymbol = toTradingViewSymbol(symbol, assetClass, region)

  useEffect(() => {
    if (!ref.current) return
    loadTradingViewWidget(
      ref.current,
      'https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js',
      {
        symbol: tvSymbol,
        width: '100%',
        colorTheme: 'dark',
        isTransparent: true,
        locale: 'pl',
      },
    )
  }, [tvSymbol])

  return (
    <div className="tradingview-quote-wrap">
      <div ref={ref} className="tradingview-widget-container tradingview-quote-container" />
    </div>
  )
}

export { presetToTvInterval }
