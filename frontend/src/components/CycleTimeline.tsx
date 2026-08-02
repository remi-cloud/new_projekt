import { AlphaModelStatus, BetaModelStatus } from '../types'

export function AlphaTimeline({ model }: { model: AlphaModelStatus }) {
  const total = model.phase_b_end_day
  const pos = Math.min(100, (model.days_since_reference / total) * 100)
  const phaseAPct = (model.phase_a_end_day / total) * 100

  return (
    <div className="timeline reveal">
      <div className="timeline-header">
        <h3>Oś czasu — Model Alpha</h3>
        <span>Dzień {model.days_since_reference}</span>
      </div>
      <div className="timeline-track">
        <div className="timeline-seg bear" style={{ width: `${phaseAPct}%` }}>
          <span>Faza spadkowa</span>
        </div>
        <div className="timeline-seg bull" style={{ width: `${100 - phaseAPct}%` }}>
          <span>Faza wzrostowa</span>
        </div>
        <div
          className="timeline-marker"
          style={{ left: `${pos}%` }}
          title={`Dzień ${model.days_since_reference}`}
        />
      </div>
      <div className="timeline-legend">
        <span className="dot bear" /> Spadki / akumulacja
        <span className="dot bull" /> Fala wzrostowa
        <span className="dot now" /> Teraz
      </div>
    </div>
  )
}

export function BetaTimeline({ model }: { model: BetaModelStatus }) {
  const phases = [
    { n: 1, label: 'Faza 1', bias: 'Słabszy → SHORT na początku', signal: 'SHORT' },
    { n: 2, label: 'Faza 2', bias: 'Najsłabszy → SHORT / późne LONG', signal: 'SHORT' },
    { n: 3, label: 'Faza 3', bias: 'Najsilniejszy', signal: 'LONG' },
    { n: 4, label: 'Faza 4', bias: 'Późno → SHORT / redukcja', signal: 'SHORT' },
  ]

  return (
    <div className="beta-phases reveal">
      <div className="timeline-header">
        <h3>Fazy — Model Beta</h3>
        <span>Faza {model.phase_number}</span>
      </div>
      <div className="beta-grid">
        {phases.map((y) => (
          <div
            key={y.n}
            className={`beta-phase${y.n === model.phase_number ? ' current' : ''}`}
          >
            <div className="beta-phase-label">{y.label}</div>
            <div className="beta-phase-bias">{y.bias}</div>
            <div className="beta-phase-signal">{y.signal}</div>
            {y.n === model.phase_number && (
              <div className="beta-phase-progress">
                <div style={{ width: `${model.phase_progress_pct}%` }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/** @deprecated aliases */
export const BitcoinTimeline = AlphaTimeline
export const PresidentialTimeline = BetaTimeline
