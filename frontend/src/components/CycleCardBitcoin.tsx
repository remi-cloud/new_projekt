import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { BitcoinCycleStatus } from '../types'

export function CycleCardBitcoin({ cycle }: { cycle: BitcoinCycleStatus }) {
  const { t } = useLocale()
  const { signal, phase } = useDomainLabels()
  const progressClass = cycle.phase === 'bear' ? 'bear' : cycle.phase === 'bull' ? 'bull' : 'neutral'

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
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
