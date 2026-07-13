import { ASSET_LABELS, SIGNAL_LABELS } from '../constants'
import { formatPrice } from '../utils/format'
import { Opportunity } from '../types'

export function OpportunityCard({ opp }: { opp: Opportunity }) {
  return (
    <div className="opp-card">
      <div className="opp-header">
        <div>
          <div className="opp-name">{opp.name}</div>
          <div className="opp-symbol">{opp.symbol}</div>
        </div>
        <span className={`signal-tag signal-${opp.action}`}>{SIGNAL_LABELS[opp.action]}</span>
      </div>
      <div className="confidence-bar">
        <div className="confidence-track">
          <div className="confidence-fill" style={{ width: `${opp.confidence}%` }} />
        </div>
        <span className="confidence-pct">{opp.confidence}%</span>
      </div>
      <div className="opp-meta">
        <span className={`tag ${opp.asset_class}`}>{ASSET_LABELS[opp.asset_class]}</span>
        <span className="tag">{opp.cycle_source === 'bitcoin_cycle' ? 'Cykl BTC' : 'Cykl prez.'}</span>
        <span className="tag">${formatPrice(opp.price, opp.asset_class)}</span>
      </div>
      <p className="opp-rationale">{opp.rationale}</p>
    </div>
  )
}
