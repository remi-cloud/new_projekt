import { useNavigate } from 'react-router-dom'
import { ASSET_LABELS, SIGNAL_LABELS } from '../constants'
import { formatPrice } from '../utils/format'
import { Opportunity } from '../types'

export function OpportunityCard({ opp }: { opp: Opportunity }) {
  const navigate = useNavigate()
  return (
    <div
      className="opp-card tap-target"
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/instrument/${encodeURIComponent(opp.symbol)}`)}
      onKeyDown={(e) => e.key === 'Enter' && navigate(`/instrument/${encodeURIComponent(opp.symbol)}`)}
    >
      <div className="opp-header">
        <div>
          <div className="opp-name">{opp.name}</div>
          <div className="opp-symbol">{opp.symbol}</div>
        </div>
        <span className={`signal-tag signal-${opp.action}`}>{SIGNAL_LABELS[opp.action]}</span>
      </div>

      <div className="price-main-row" style={{ marginBottom: 10 }}>
        <span className="price-live" style={{ fontSize: '1.2rem' }}>
          ${formatPrice(opp.price, opp.asset_class)}
        </span>
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
        {opp.is_momentum_pick && (
          <span className="tag momentum-pick">⚡ Momentum</span>
        )}
        {opp.momentum_score != null && (
          <span className="tag momentum-score">Mom. {opp.momentum_score.toFixed(0)}</span>
        )}
      </div>
      <p className="opp-rationale">{opp.rationale}</p>
      <span className="tap-hint">Zobacz wykres →</span>
    </div>
  )
}
