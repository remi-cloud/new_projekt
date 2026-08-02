import { BitcoinCycleStatus, PresidentialCycleStatus } from '../types'

export function BitcoinTimeline({ cycle }: { cycle: BitcoinCycleStatus }) {
  const total = cycle.bull_phase_end_day
  const pos = Math.min(100, (cycle.days_since_ath / total) * 100)
  const bearPct = (cycle.bear_phase_end_day / total) * 100

  return (
    <div className="timeline reveal">
      <div className="timeline-header">
        <h3>Oś czasu — Model Alpha</h3>
        <span>Dzień {cycle.days_since_ath}</span>
      </div>
      <div className="timeline-track">
        <div className="timeline-seg bear" style={{ width: `${bearPct}%` }}>
          <span>Faza spadkowa</span>
        </div>
        <div className="timeline-seg bull" style={{ width: `${100 - bearPct}%` }}>
          <span>Faza wzrostowa</span>
        </div>
        <div className="timeline-marker" style={{ left: `${pos}%` }} title={`Dzień ${cycle.days_since_ath}`} />
      </div>
      <div className="timeline-legend">
        <span className="dot bear" /> Spadki / akumulacja
        <span className="dot bull" /> Fala wzrostowa
        <span className="dot now" /> Teraz
      </div>
    </div>
  )
}

export function PresidentialTimeline({ cycle }: { cycle: PresidentialCycleStatus }) {
  const years = [
    { n: 1, label: 'Faza 1', bias: 'Słabszy', signal: 'Obserwuj' },
    { n: 2, label: 'Faza 2', bias: 'Najsłabszy → kupuj dołki', signal: 'Kupuj' },
    { n: 3, label: 'Faza 3', bias: 'Najsilniejszy', signal: 'Kupuj' },
    { n: 4, label: 'Faza 4', bias: 'Umiarkowany', signal: 'Trzymaj' },
  ]

  return (
    <div className="pres-years reveal">
      <div className="timeline-header">
        <h3>Fazy — Model Beta</h3>
        <span>Faza {cycle.year_number}</span>
      </div>
      <div className="pres-grid">
        {years.map((y) => (
          <div
            key={y.n}
            className={`pres-year${y.n === cycle.year_number ? ' current' : ''}`}
          >
            <div className="pres-year-label">{y.label}</div>
            <div className="pres-year-bias">{y.bias}</div>
            <div className="pres-year-signal">{y.signal}</div>
            {y.n === cycle.year_number && (
              <div className="pres-year-progress">
                <div style={{ width: `${cycle.year_progress_pct}%` }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
