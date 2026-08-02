import { PHASE_LABELS } from '../lib/labels'
import { AlphaModelStatus, BetaModelStatus } from '../types'
import SignalTag from './SignalTag'

export function CycleCardAlpha({ model }: { model: AlphaModelStatus }) {
  const progressClass =
    model.phase === 'bear' ? 'bear' : model.phase === 'bull' ? 'bull' : 'dist'
  return (
    <section className="cycle-card alpha reveal">
      <div className="cycle-card-header">
        <h2>Model Alpha</h2>
        <SignalTag action={model.signal} />
      </div>
      <p className="cycle-sub">Warstwa sygnałowa — aktywa cyfrowe</p>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Referencja</div>
          <div className="stat-value">${model.reference_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Cena bieżąca</div>
          <div className="stat-value">${model.current_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Dni od referencji</div>
          <div className="stat-value">{model.days_since_reference}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Faza</div>
          <div className="stat-value">{PHASE_LABELS[model.phase] ?? model.phase}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div
          className={`progress-fill ${progressClass}`}
          style={{ width: `${model.phase_progress_pct}%` }}
        />
      </div>
      <div className="progress-meta">
        Postęp fazy: {model.phase_progress_pct}% · Pozostało {model.days_remaining_in_phase} dni
      </div>
      <p className="cycle-rationale">{model.rationale}</p>
    </section>
  )
}

export function CycleCardBeta({ model }: { model: BetaModelStatus }) {
  return (
    <section className="cycle-card beta reveal">
      <div className="cycle-card-header">
        <h2>Model Beta</h2>
        <SignalTag action={model.signal} />
      </div>
      <p className="cycle-sub">Warstwa sygnałowa — rynki tradycyjne</p>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Okres</div>
          <div className="stat-value">Aktywny</div>
        </div>
        <div className="stat">
          <div className="stat-label">Faza modelu</div>
          <div className="stat-value">{PHASE_LABELS[model.current_phase] ?? model.current_phase}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Dzień fazy</div>
          <div className="stat-value">{model.days_into_phase}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Bias historyczny</div>
          <div className="stat-value stat-value-sm">{model.historical_bias.split('—')[0]}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div className="progress-fill teal" style={{ width: `${model.phase_progress_pct}%` }} />
      </div>
      <div className="progress-meta">
        Postęp fazy: {model.phase_progress_pct}% · Pozostało {model.days_remaining_in_phase} dni
      </div>
      <p className="cycle-rationale">{model.rationale}</p>
    </section>
  )
}

/** @deprecated aliases */
export const CycleCardBitcoin = CycleCardAlpha
export const CycleCardPresidential = CycleCardBeta
