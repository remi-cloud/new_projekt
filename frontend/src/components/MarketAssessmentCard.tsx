import { ASSET_LABELS, PHASE_LABELS, REGION_LABELS, SIGNAL_LABELS } from '../constants'
import { formatPrice } from '../utils/format'
import { AssetCycleAssessment } from '../types'

export function MarketAssessmentCard({ item }: { item: AssetCycleAssessment }) {
  return (
    <article className="market-card">
      <div className="market-card-top">
        <div>
          <div className="market-name">{item.name}</div>
          <div className="market-symbol">{item.symbol}</div>
        </div>
        <span className={`signal-tag signal-${item.signal}`}>{SIGNAL_LABELS[item.signal]}</span>
      </div>

      <div className="market-price-row">
        <span className="market-price">${formatPrice(item.price, item.asset_class)}</span>
        {item.change_pct_7d !== null && (
          <span className={item.change_pct_7d >= 0 ? 'change-positive' : 'change-negative'}>
            {item.change_pct_7d >= 0 ? '+' : ''}{item.change_pct_7d}% (7d)
          </span>
        )}
      </div>

      <div className="confidence-bar">
        <div className="confidence-track">
          <div className="confidence-fill" style={{ width: `${item.confidence}%` }} />
        </div>
        <span className="confidence-pct">{item.confidence}%</span>
      </div>

      <div className="market-tags">
        <span className={`tag ${item.asset_class}`}>{ASSET_LABELS[item.asset_class]}</span>
        <span className="tag region">{REGION_LABELS[item.region] ?? item.region}</span>
        <span className="tag">{PHASE_LABELS[item.price_phase] ?? item.price_phase}</span>
        {item.drawdown_from_high_pct !== null && (
          <span className="tag">-{item.drawdown_from_high_pct}% ATH</span>
        )}
      </div>

      <p className="market-rationale">{item.rationale}</p>
    </article>
  )
}

export function MarketSummaryBanner({ summary }: { summary: import('../types').MarketSummary }) {
  const outlookClass = summary.outlook === 'bullish' ? 'bullish' : summary.outlook === 'bearish' ? 'bearish' : 'mixed'
  return (
    <div className={`market-summary ${outlookClass}`}>
      <div className="market-summary-title">Ocena globalna · {summary.total_assets} instrumentów</div>
      <div className="market-summary-text">{summary.outlook_label}</div>
      <div className="market-summary-stats">
        <span>Kupuj: {summary.by_signal.buy ?? 0}</span>
        <span>Obserwuj: {summary.by_signal.watch ?? 0}</span>
        <span>Trzymaj: {summary.by_signal.hold ?? 0}</span>
        <span>Sprzedaj: {summary.by_signal.sell ?? 0}</span>
      </div>
    </div>
  )
}
