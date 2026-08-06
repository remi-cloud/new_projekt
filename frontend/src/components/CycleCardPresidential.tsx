import type { ReactNode } from 'react'
import { useState } from 'react'
import { IntramonthSeasonalityPanel } from './IntramonthSeasonalityPanel'
import { MonthPumpSnippet } from './MonthPumpSnippet'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import {
  PresidentialCycleStatus,
  PresidentialMonthReturn,
  PresidentialYearMonthRow,
  PresidentialYearReturn,
} from '../types'

const CHART_MAX_PCT = 18
const CHART_TICKS = [0, 8, 16]
const MONTH_KEYS = [
  'monthJan',
  'monthFeb',
  'monthMar',
  'monthApr',
  'monthMay',
  'monthJun',
  'monthJul',
  'monthAug',
  'monthSep',
  'monthOct',
  'monthNov',
  'monthDec',
] as const

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

function HeatmapCell({
  item,
  selected,
  onSelect,
}: {
  item: PresidentialMonthReturn
  selected?: boolean
  onSelect?: (month: number) => void
}) {
  const { t } = useLocale()
  const key = MONTH_KEYS[item.month - 1]
  const label = t(`cyclesCard.${key}`)
  const up = item.bias === 'up' || item.avg_return_pct >= 0
  return (
    <button
      type="button"
      className={`pres-heat-cell clickable ${up ? 'up' : 'down'} ${item.is_current ? 'active' : ''} ${selected ? 'selected' : ''}`}
      title={`${label}: ${formatReturn(item.avg_return_pct)} — ${t('cyclesCard.intramonthHint')}`}
      onClick={() => onSelect?.(item.month)}
    >
      {formatReturn(item.avg_return_pct)}
    </button>
  )
}

function MonthHeatmap({
  rows,
  title,
  chip,
  note,
  selectedMonth,
  onSelectMonth,
}: {
  rows: PresidentialYearMonthRow[]
  title: string
  chip?: ReactNode
  note?: string
  selectedMonth?: number | null
  onSelectMonth?: (month: number) => void
}) {
  const { t } = useLocale()
  const { phase } = useDomainLabels()
  if (!rows.length) return null

  return (
    <div className="pres-month-seasonality">
      <div className="pres-month-head">
        <span className="pres-month-title">{title}</span>
        {chip}
      </div>
      {note && <p className="pres-next-term-note">{note}</p>}
      <p className="pres-next-term-note">{t('cyclesCard.intramonthHint')}</p>
      <div className="pres-heat-table" role="table">
        <div className="pres-heat-row head" role="row">
          <div className="pres-heat-year" role="columnheader">
            {t('cyclesCard.termYear')}
          </div>
          {MONTH_KEYS.map((key) => (
            <div key={key} className="pres-heat-cell head" role="columnheader">
              {t(`cyclesCard.${key}`)}
            </div>
          ))}
        </div>
        {rows.map((row) => (
          <div
            key={`${row.year}-${row.calendar_year ?? row.year_number}`}
            className={`pres-heat-row ${row.is_current ? 'current' : ''}`}
            role="row"
          >
            <div className="pres-heat-year" role="cell">
              <span>{phase(row.year)}</span>
              {row.calendar_year != null && (
                <em className="pres-heat-cal">{row.calendar_year}</em>
              )}
            </div>
            {row.months.map((m) => (
              <HeatmapCell
                key={m.month}
                item={m}
                selected={selectedMonth === m.month}
                onSelect={onSelectMonth}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function CycleCardPresidential({ cycle }: { cycle: PresidentialCycleStatus }) {
  const { t } = useLocale()
  const { signal, phase } = useDomainLabels()
  const [openMonth, setOpenMonth] = useState<number | null>(null)
  const yearReturns = cycle.year_returns ?? []
  const monthMatrices = cycle.month_matrices ?? []
  const monthReturns = cycle.month_returns ?? []
  const currentReturn = cycle.current_year_expected_return_pct ?? 0
  const cycleAvg = cycle.cycle_avg_return_pct ?? 8.5
  const currentYearLabel = phase(cycle.current_year)
  const season = cycle.calendar_season === 'worst_six' ? 'worst_six' : 'best_six'
  const universeN = cycle.seasonality_universe_size ?? 0
  const next = cycle.next_term_outlook
  const seasonChip = (
    <span className={`pres-season-chip season-${season}`}>
      {season === 'best_six' ? t('cyclesCard.bestSix') : t('cyclesCard.worstSix')}
    </span>
  )
  const toggleMonth = (m: number) => setOpenMonth((cur) => (cur === m ? null : m))

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

      {monthMatrices.length === 4 ? (
        <MonthHeatmap
          rows={monthMatrices}
          title={t('cyclesCard.monthSeasonalityAll', {
            president: cycle.president,
            n: universeN,
          })}
          chip={seasonChip}
          selectedMonth={openMonth}
          onSelectMonth={toggleMonth}
        />
      ) : (
        monthReturns.length === 12 && (
          <div className="pres-month-seasonality">
            <div className="pres-month-head">
              <span className="pres-month-title">
                {t('cyclesCard.monthSeasonality', { year: currentYearLabel, n: universeN })}
              </span>
              {seasonChip}
            </div>
            <p className="pres-next-term-note">{t('cyclesCard.intramonthHint')}</p>
            <div className="pres-month-grid">
              {monthReturns.map((m) => {
                const key = MONTH_KEYS[m.month - 1]
                const label = t(`cyclesCard.${key}`)
                const up = m.bias === 'up' || m.avg_return_pct >= 0
                return (
                  <button
                    type="button"
                    key={m.month}
                    className={`pres-month-cell clickable ${up ? 'up' : 'down'} ${m.is_current ? 'active' : ''} ${openMonth === m.month ? 'selected' : ''}`}
                    title={`${label}: ${formatReturn(m.avg_return_pct)}`}
                    onClick={() => toggleMonth(m.month)}
                  >
                    <span className="pres-month-label">{label}</span>
                    <span className="pres-month-value">{formatReturn(m.avg_return_pct)}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )
      )}

      {openMonth != null && (
        <>
          <MonthPumpSnippet month={openMonth} />
          <IntramonthSeasonalityPanel
            month={openMonth}
            universe="us"
            onClose={() => setOpenMonth(null)}
          />
        </>
      )}

      {next && next.year_rows?.length === 4 && (
        <MonthHeatmap
          rows={next.year_rows}
          title={t('cyclesCard.postTermTitle', {
            start: next.term_start.slice(0, 4),
            end: next.term_end.slice(0, 4),
          })}
          note={next.note || t('cyclesCard.postTermNote')}
          selectedMonth={openMonth}
          onSelectMonth={toggleMonth}
        />
      )}

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
