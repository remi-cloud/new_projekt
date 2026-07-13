import { SIGNAL_LABELS } from '../constants'
import { RegionalCycleSnapshot } from '../types'

const REGION_COLORS: Record<string, string> = {
  us: 'presidential',
  pl: 'polish',
  eu: 'europe',
  asia: 'asia',
  em: 'em',
  global: 'global',
}

export function CycleCardRegional({ cycle }: { cycle: RegionalCycleSnapshot }) {
  const colorClass = REGION_COLORS[cycle.region] ?? 'global'
  return (
    <div className={`cycle-card regional ${colorClass}`}>
      <div className="cycle-card-header">
        <h2>{cycle.region_label}</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{SIGNAL_LABELS[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Faza</div>
          <div className="stat-value stat-small">{cycle.phase.replace(/_/g, ' ')}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Waga kupna</div>
          <div className="stat-value">{Math.round(cycle.buy_weight * 100)}%</div>
        </div>
        <div className="stat">
          <div className="stat-label">Bias</div>
          <div className="stat-value stat-small">{cycle.bias.split('—')[0]}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div className="progress-fill neutral" style={{ width: `${cycle.buy_weight * 100}%` }} />
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
