import { SIGNAL_LABELS, PHASE_LABELS } from '../constants'
import { PresidentialCycleStatus } from '../types'

const YEAR_BARS = [
  { key: 'year_1', label: 'Rok 1', bias: 'Słaby', strength: 30 },
  { key: 'year_2', label: 'Rok 2', bias: 'Najsłabszy', strength: 20 },
  { key: 'year_3', label: 'Rok 3', bias: 'Najsilniejszy', strength: 100 },
  { key: 'year_4', label: 'Rok 4', bias: 'Umiarkowany', strength: 55 },
]

export function CycleCardPresidential({ cycle }: { cycle: PresidentialCycleStatus }) {
  return (
    <div className="cycle-card presidential">
      <div className="cycle-card-header">
        <h2>Cykl prezydencki USA</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{SIGNAL_LABELS[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Prezydent</div>
          <div className="stat-value">{cycle.president}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Rok kadencji</div>
          <div className="stat-value">{PHASE_LABELS[cycle.current_year] ?? cycle.current_year}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Dzień roku</div>
          <div className="stat-value">{cycle.days_into_year}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Historyczny bias</div>
          <div className="stat-value stat-small">{cycle.historical_bias.split('—')[0]}</div>
        </div>
      </div>
      <div className="pres-year-chart">
        {YEAR_BARS.map((y) => (
          <div key={y.key} className={`pres-bar-wrap ${cycle.current_year === y.key ? 'active' : ''}`}>
            <div className="pres-bar" style={{ height: `${y.strength}%` }} />
            <span>{y.label}</span>
          </div>
        ))}
      </div>
      <div className="progress-bar">
        <div className="progress-fill neutral" style={{ width: `${cycle.year_progress_pct}%` }} />
      </div>
      <div className="phase-meta">
        Postęp roku: {cycle.year_progress_pct}% · Pozostało {cycle.days_remaining_in_year} dni
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
