import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
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
  const { t } = useLocale()
  const { phase } = useDomainLabels()
  const positive = item.avg_return_pct >= 0
  const label = phase(item.year)

  return (
    <div
      className={`pres-return-col ${item.is_current ? 'active' : ''} tone-${item.tone}`}
      title={t('cyclesCard.returnTooltip', {
        label,
        return: formatReturn(item.avg_return_pct),
        bias: item.bias,
      })}
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
      <span className="pres-return-label">{label}</span>
      {item.is_current && <span className="pres-return-active-dot" aria-hidden />}
    </div>
  )
}

export function CycleCardPresidential({ cycle }: { cycle: PresidentialCycleStatus }) {
  const { t } = useLocale()
  const { signal, phase } = useDomainLabels()
  const yearReturns = cycle.year_returns ?? []
  const currentReturn = cycle.current_year_expected_return_pct ?? 0
  const cycleAvg = cycle.cycle_avg_return_pct ?? 8.5
  const currentYearLabel = phase(cycle.current_year)

  return (
    <div className="cycle-card presidential">
      <div className="cycle-card-header">
        <h2>{t('cyclesCard.presTitle')}</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{signal[cycle.signal]}</span>
      </div>

      <div className="cycle-stats pres-cycle-stats">
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.president')}</div>
          <div className="stat-value">{cycle.president}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.termYear')}</div>
          <div className="stat-value">{currentYearLabel}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.historicalReturn')}</div>
          <div className={`stat-value ${currentReturn >= cycleAvg ? 'positive' : 'negative'}`}>
            {formatReturn(currentReturn)}
            <em>{t('cyclesCard.perYear')}</em>
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.cycleAvg')}</div>
          <div className="stat-value stat-small">{formatReturn(cycleAvg)}</div>
        </div>
      </div>

      <div className="pres-return-chart-wrap">
        <div className="pres-return-chart-head">
          <span className="pres-return-chart-title">
            {t('cyclesCard.benchmarkChange', { benchmark: cycle.benchmark ?? 'S&P 500' })}
          </span>
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
              <span>{t('cyclesCard.avg', { n: formatReturn(cycleAvg) })}</span>
            </div>
            {yearReturns.map((item) => (
              <ReturnBar key={item.year} item={item} />
            ))}
          </div>
        </div>

        <div className="pres-return-legend">
          <span className="pres-legend-item tone-weak">{t('cyclesCard.weakest')}</span>
          <span className="pres-legend-item tone-moderate">{t('cyclesCard.moderate')}</span>
          <span className="pres-legend-item tone-best">{t('cyclesCard.strongest')}</span>
        </div>
      </div>

      <div className="pres-year-progress">
        <div className="pres-year-progress-head">
          <span>
            {t('cyclesCard.progress')} {currentYearLabel}
          </span>
          <span className="tabular">
            {cycle.year_progress_pct}% · {cycle.days_remaining_in_year} {t('cyclesCard.days')}
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
