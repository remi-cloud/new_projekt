import { AssetClass } from '../types'
import { ChartResponse } from '../types/chart'
import { formatPrice } from '../utils/format'

function changeFromPct(price: number, pct: number): number {
  if (!pct) return 0
  const prev = price / (1 + pct / 100)
  return price - prev
}

interface PriceHeaderProps {
  name: string
  symbol: string
  assetClass: AssetClass
  chart?: ChartResponse | null
  fallbackPrice: number
  /** Cena z live tickera (dashboard) — ma priorytet nad cache wykresu */
  livePrice?: number
  change24h?: number | null
  change7d?: number | null
  signalLabel?: string
  signalAction?: string
  compact?: boolean
}

export function PriceHeader({
  name,
  symbol,
  assetClass,
  chart,
  fallbackPrice,
  livePrice,
  change24h,
  change7d,
  signalLabel,
  signalAction,
  compact,
}: PriceHeaderProps) {
  const price = livePrice ?? chart?.current_price ?? fallbackPrice ?? 0
  const changePct = chart?.change_pct ?? change24h ?? 0
  const change = chart?.change ?? changeFromPct(price, changePct)
  const isUp = changePct >= 0
  const currency = chart?.currency === 'USD' || !chart?.currency ? '$' : `${chart.currency} `

  return (
    <div className={`price-header ${compact ? 'compact' : ''}`}>
      <div className="price-header-top">
        <div className="price-header-symbol">
          <span className="price-ticker">{symbol}</span>
          <span className="price-name">{name}</span>
        </div>
        {signalLabel && signalAction && (
          <span className={`signal-tag signal-${signalAction}`}>{signalLabel}</span>
        )}
      </div>

      <div className="price-main-row">
        <span className="price-live tabular">{currency}{formatPrice(price, assetClass)}</span>
        <div className={`price-change-block ${isUp ? 'up' : 'down'}`}>
          <span className="price-change-abs">
            {isUp ? '+' : ''}{currency}{Math.abs(change).toFixed(assetClass === 'forex' ? 4 : 2)}
          </span>
          <span className="price-change-pct">
            {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{changePct.toFixed(2)}%
          </span>
        </div>
      </div>

      {!compact && (
        <div className="price-meta-row">
          {chart?.day_high != null && (
            <span>H: <b>{currency}{formatPrice(chart.day_high, assetClass)}</b></span>
          )}
          {chart?.day_low != null && (
            <span>L: <b>{currency}{formatPrice(chart.day_low, assetClass)}</b></span>
          )}
          {change7d != null && (
            <span className={change7d >= 0 ? 'change-positive' : 'change-negative'}>
              7d: {change7d >= 0 ? '+' : ''}{change7d.toFixed(2)}%
            </span>
          )}
        </div>
      )}
    </div>
  )
}
