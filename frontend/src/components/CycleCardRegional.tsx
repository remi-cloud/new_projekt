import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { RegionalCycleSnapshot } from '../types'

const REGION_COLORS: Record<string, string> = {
  us: 'presidential',
  pl: 'polish',
  eu: 'europe',
  asia: 'asia',
  em: 'em',
  global: 'global',
}

export function CycleCardRegional({ cycle }: { cycle: RegionalCycleSnapshot }) {
  const { t } = useLocale()
  const { signal, phase } = useDomainLabels()
  const colorClass = REGION_COLORS[cycle.region] ?? 'global'

  return (
    <div className={`cycle-card regional ${colorClass}`}>
      <div className="cycle-card-header">
        <h2>{cycle.region_label}</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{signal[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.regionalPhase')}</div>
          <div className="stat-value stat-small">{phase(cycle.phase)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.buyWeight')}</div>
          <div className="stat-value">{Math.round(cycle.buy_weight * 100)}%</div>
        </div>
        <div className="stat">
          <div className="stat-label">{t('cyclesCard.bias')}</div>
          <div className="stat-value stat-small">{cycle.bias.split('—')[0]}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div className="progress-fill neutral" style={{ width: `${cycle.buy_weight * 100}%` }} />
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}
