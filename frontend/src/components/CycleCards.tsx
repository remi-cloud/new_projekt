import { PHASE_LABELS } from '../lib/labels'
import { BitcoinCycleStatus, PresidentialCycleStatus } from '../types'
import SignalTag from './SignalTag'

export function CycleCardBitcoin({ cycle }: { cycle: BitcoinCycleStatus }) {
  const progressClass =
    cycle.phase === 'bear' ? 'bear' : cycle.phase === 'bull' ? 'bull' : 'dist'
  return (
    <section className="cycle-card bitcoin reveal">
      <div className="cycle-card-header">
        <h2>Cykl Bitcoin</h2>
        <SignalTag action={cycle.signal} />
      </div>
      <p className="cycle-sub">364 dni spadków · 1064 dni wzrostu od ATH</p>
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
      <div className="progress-bar">
        <div
          className={`progress-fill ${progressClass}`}
          style={{ width: `${cycle.phase_progress_pct}%` }}
        />
      </div>
      <div className="progress-meta">
        Postęp fazy: {cycle.phase_progress_pct}% · Pozostało {cycle.days_remaining_in_phase} dni
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </section>
  )
}

export function CycleCardPresidential({ cycle }: { cycle: PresidentialCycleStatus }) {
  return (
    <section className="cycle-card presidential reveal">
      <div className="cycle-card-header">
        <h2>Cykl prezydencki USA</h2>
        <SignalTag action={cycle.signal} />
      </div>
      <p className="cycle-sub">Bias historyczny lat 1–4 kadencji</p>
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
          <div className="stat-value stat-value-sm">{cycle.historical_bias.split('—')[0]}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div className="progress-fill teal" style={{ width: `${cycle.year_progress_pct}%` }} />
      </div>
      <div className="progress-meta">
        Postęp roku: {cycle.year_progress_pct}% · Pozostało {cycle.days_remaining_in_year} dni
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </section>
  )
}
