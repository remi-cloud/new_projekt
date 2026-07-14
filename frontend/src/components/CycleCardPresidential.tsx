import { SIGNAL_LABELS, PHASE_LABELS } from '../constants'
import { PresidentialCycleStatus, PresidentialYearReturn } from '../types'

const CHART_MAX_PCT = 18
const CHART_TICKS = [0, 8, 16]

function formatReturn(pct: number): string {
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)}%`
}

function barHeight(pct: number): number {
  return Math.max(6, (Math.abs(pct) / CHART_MAX_PCT) * 100)
}

function ReturnBar({ item }: { item: PresidentialYearReturn }) {
  const positive = item.avg_return_pct >= 0
  return (
    <div
      className={`pres-return-col ${item.is_current ? 'active' : ''} tone-${item.tone}`}
      title={`${item.label}: średnio ${formatReturn(item.avg_return_pct)}/rok · ${item.bias}`}
    >
      <span className={`pres-return-value ${positive ? 'positive' : 'negative'}`}>
        {formatReturn(item.avg_return_pct)}
      </span>
      <div className="pres-return-bar-track">
        <div
          className={`pres-return-bar ${positive ? 'up' : 'down'}`}
          style={{ height: `${barHeight(item.avg_return_pct)}%` }}
        />
      </div>
      <span className="pres-return-label">{item.label}</span>
      {item.is_current && <span className="pres-return-active-dot" aria-hidden />}
    </div>
  )
}

export function CycleCardPresidential({ cycle }: { cycle: PresidentialCycleStatus }) {
  const yearReturns = cycle.year_returns ?? []
  const currentReturn = cycle.current_year_expected_return_pct ?? 0
  const cycleAvg = cycle.cycle_avg_return_pct ?? 8.5

  return (
    <div className="cycle-card presidential">
      <div className="cycle-card-header">
        <h2>Cykl prezydencki USA</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{SIGNAL_LABELS[cycle.signal]}</span>
      </div>

      <div className="cycle-stats pres-cycle-stats">
        <div className="stat">
          <div className="stat-label">Prezydent</div>
          <div className="stat-value">{cycle.president}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Rok kadencji</div>
          <div className="stat-value">{PHASE_LABELS[cycle.current_year] ?? cycle.current_year}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Historyczny zwrot</div>
          <div className={`stat-value ${currentReturn >= cycleAvg ? 'positive' : 'negative'}`}>
            {formatReturn(currentReturn)}
            <em>/rok</em>
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">Średnia cyklu</div>
          <div className="stat-value stat-small">{formatReturn(cycleAvg)}</div>
        </div>
      </div>

      <div className="pres-return-chart-wrap">
        <div className="pres-return-chart-head">
          <span className="pres-return-chart-title">{cycle.benchmark ?? 'S&P 500'} · roczna zmiana</span>
          <span className="pres-return-chart-note">{cycle.benchmark_note}</span>
        </div>

        <div className="pres-return-chart">
          <div className="pres-return-y-axis" aria-hidden>
            {CHART_TICKS.slice()
              .reverse()
              .map((tick) => (
                <span key={tick}>{tick}%</span>
              ))}
          </div>

          <div className="pres-return-bars">
            <div className="pres-return-zero-line" aria-hidden />
            <div className="pres-return-avg-line" style={{ bottom: `${barHeight(cycleAvg)}%` }}>
              <span>śr. {formatReturn(cycleAvg)}</span>
            </div>
            {yearReturns.map((item) => (
              <ReturnBar key={item.year} item={item} />
            ))}
          </div>
        </div>

        <div className="pres-return-legend">
          <span className="pres-legend-item tone-weak">Najsłabszy</span>
          <span className="pres-legend-item tone-moderate">Umiarkowany</span>
          <span className="pres-legend-item tone-best">Najsilniejszy</span>
        </div>
      </div>

      <div className="pres-year-progress">
        <div className="pres-year-progress-head">
          <span>
            Postęp {PHASE_LABELS[cycle.current_year] ?? `Rok ${cycle.year_number}`}
          </span>
          <span className="tabular">
            {cycle.year_progress_pct}% · {cycle.days_remaining_in_year} dni
          </span>
        </div>
        <div className="progress-bar">
          <div
            className={`progress-fill pres-progress-fill tone-${yearReturns.find((y) => y.is_current)?.tone ?? 'moderate'}`}
            style={{ width: `${cycle.year_progress_pct}%` }}
          />
        </div>
      </div>

      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
