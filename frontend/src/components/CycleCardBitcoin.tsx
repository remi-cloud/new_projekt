import { useState } from 'react'
import { IntramonthSeasonalityPanel } from './IntramonthSeasonalityPanel'
import { MonthPumpSnippet } from './MonthPumpSnippet'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { BitcoinCycleStatus, BitcoinMonthReturn } from '../types'

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

function MonthCell({
  item,
  selected,
  onSelect,
}: {
  item: BitcoinMonthReturn
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
      className={`pres-month-cell clickable ${up ? 'up' : 'down'} ${item.is_current ? 'active' : ''} ${selected ? 'selected' : ''}`}
      title={`${label}: ${formatReturn(item.avg_return_pct)} — ${t('cyclesCard.intramonthHint')}`}
      onClick={() => onSelect?.(item.month)}
    >
      <span className="pres-month-label">{label}</span>
      <span className="pres-month-value">{formatReturn(item.avg_return_pct)}</span>
    </button>
  )
}

export function CycleCardBitcoin({ cycle }: { cycle: BitcoinCycleStatus }) {
  const { t } = useLocale()
  const { signal, phase } = useDomainLabels()
  const [openMonth, setOpenMonth] = useState<number | null>(null)
  const progressClass = cycle.phase === 'bear' ? 'bear' : cycle.phase === 'bull' ? 'bull' : 'neutral'
  const monthReturns = cycle.month_returns ?? []
  const season = cycle.calendar_season === 'worst_six' ? 'worst_six' : 'best_six'
  const cmp = cycle.spx_comparison
  const corr =
    cmp?.corr_rolling_24m_latest != null
      ? cmp.corr_rolling_24m_latest.toFixed(2)
      : cmp?.corr_full != null
        ? cmp.corr_full.toFixed(2)
        : '—'

  return (
    <div className="cycle-card bitcoin">
      <div className="cycle-card-header">
        <h2>{t('cyclesCard.btcTitle')}</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{signal[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.lastAth')}</div>
          <div className="stat-value">${cycle.last_ath_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.currentPrice')}</div>
          <div className="stat-value">${cycle.current_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.daysSinceAth')}</div>
          <div className="stat-value">{cycle.days_since_ath}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.phase')}</div>
          <div className="stat-value">{phase(cycle.phase)}</div>
        </div>
      </div>
      <div className="timeline-visual">
        <div className="timeline-segment bear" style={{ flex: cycle.bear_phase_end_day }}>
          <span>
            {t('cyclesCard.declines')}
            <br />
            {cycle.bear_phase_end_day}d
          </span>
        </div>
        <div className="timeline-segment bull" style={{ flex: cycle.bull_phase_end_day - cycle.bear_phase_end_day }}>
          <span>
            {t('cyclesCard.growth')}
            <br />
            1064d
          </span>
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
        {t('cyclesCard.phaseProgress', {
          pct: cycle.phase_progress_pct,
          days: cycle.days_remaining_in_phase,
        })}
      </div>

      {monthReturns.length === 12 && (
        <div className="pres-month-seasonality">
          <div className="pres-month-head">
            <span className="pres-month-title">{t('cyclesCard.btcMonthSeasonality')}</span>
            <span className={`pres-season-chip season-${season}`}>
              {season === 'best_six' ? t('cyclesCard.bestSix') : t('cyclesCard.worstSix')}
            </span>
          </div>
          <p className="pres-next-term-note">{t('cyclesCard.intramonthHint')}</p>
          <div className="pres-month-grid">
            {monthReturns.map((m) => (
              <MonthCell
                key={m.month}
                item={m}
                selected={openMonth === m.month}
                onSelect={(month) => setOpenMonth((cur) => (cur === month ? null : month))}
              />
            ))}
          </div>
          {cmp && (
            <div className="phase-meta" style={{ marginTop: '0.5rem' }}>
              {t('cyclesCard.btcVsSpx', {
                verdict: cmp.verdict ?? '—',
                regime: cmp.regime ?? '—',
                corr,
              })}
            </div>
          )}
        </div>
      )}

      {openMonth != null && (
        <>
          <MonthPumpSnippet month={openMonth} />
          <IntramonthSeasonalityPanel
            month={openMonth}
            universe="btc"
            onClose={() => setOpenMonth(null)}
          />
        </>
      )}

      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
