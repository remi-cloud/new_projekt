import { Link } from 'react-router-dom'
import { ASSET_LABELS, formatModel, formatPrice } from '../lib/labels'
import { positionPath } from '../lib/routes'
import { Opportunity } from '../types'
import SignalTag from './SignalTag'

export default function OpportunityCard({ opp }: { opp: Opportunity }) {
  return (
    <Link to={positionPath(opp.symbol)} className="opp-card opp-card-link">
      <div className="opp-header">
        <div>
          <div className="opp-name">{opp.name}</div>
          <div className="opp-symbol">{opp.symbol}</div>
        </div>
        <SignalTag action={opp.action} />
      </div>
      <div className="confidence-bar">
        <div className="confidence-track">
          <div className="confidence-fill" style={{ width: `${opp.confidence}%` }} />
        </div>
        <span className="confidence-pct">{opp.confidence}%</span>
      </div>
      <div className="opp-meta">
        <span className={`tag ${opp.asset_class}`}>{ASSET_LABELS[opp.asset_class]}</span>
        <span className="tag">{formatModel(opp.cycle_source)}</span>
        <span className="tag">${formatPrice(opp.price, opp.asset_class)}</span>
      </div>
      <p className="opp-rationale">{opp.rationale}</p>
      <span className="opp-open">Otwórz pozycję →</span>
    </Link>
  )
}
