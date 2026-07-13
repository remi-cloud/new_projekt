import { SIGNAL_LABELS, PHASE_LABELS } from '../constants'
import { BitcoinCycleStatus } from '../types'

export function CycleCardBitcoin({ cycle }: { cycle: BitcoinCycleStatus }) {
  const progressClass = cycle.phase === 'bear' ? 'bear' : cycle.phase === 'bull' ? 'bull' : 'neutral'

  return (
    <div className="cycle-card bitcoin">
      <div className="cycle-card-header">
        <h2>Cykl Bitcoin (364 / 1064 dni)</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{SIGNAL_LABELS[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Ostatnie ATH</div>
          <div className="stat-value">${cycle.last_ath_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Cena bieżąca</div>
          <div className="stat-value">${cycle.current_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Dni od ATH</div>
          <div className="stat-value">{cycle.days_since_ath}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Faza</div>
          <div className="stat-value">{PHASE_LABELS[cycle.phase] ?? cycle.phase}</div>
        </div>
      </div>
      <div className="timeline-visual">
        <div className="timeline-segment bear" style={{ flex: cycle.bear_phase_end_day }}>
          <span>Spadki<br />{cycle.bear_phase_end_day}d</span>
        </div>
        <div className="timeline-segment bull" style={{ flex: cycle.bull_phase_end_day - cycle.bear_phase_end_day }}>
          <span>Wzrost<br />1064d</span>
        </div>
        <div
          className="timeline-marker"
          style={{
            left: `${Math.min(99, (cycle.days_since_ath / cycle.bull_phase_end_day) * 100)}%`,
          }}
        />
      </div>
      <div className="progress-bar">
        <div className={`progress-fill ${progressClass}`} style={{ width: `${cycle.phase_progress_pct}%` }} />
      </div>
      <div className="phase-meta">
        Postęp fazy: {cycle.phase_progress_pct}% · Pozostało {cycle.days_remaining_in_phase} dni
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
