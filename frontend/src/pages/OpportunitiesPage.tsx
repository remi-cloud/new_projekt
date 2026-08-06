import { useMemo, useState } from 'react'
import { OpportunityCard } from '../components/OpportunityCard'
import { FilterChips } from '../components/FilterChips'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { AssetClass, SignalAction } from '../types'

export function OpportunitiesPage() {
  const { data, error, reload, loading } = useDashboardContext()
  const { t } = useLocale()
  const { asset, signal } = useDomainLabels()
  const [filterClass, setFilterClass] = useState<AssetClass | 'all'>('all')
  const [filterAction, setFilterAction] = useState<SignalAction | 'all'>('all')
  const [filterMomentum, setFilterMomentum] = useState<'all' | 'momentum'>('all')

  const filtered = useMemo(() => {
    if (!data) return []
    return data.opportunities.filter((o) => {
      if (filterClass !== 'all' && o.asset_class !== filterClass) return false
      if (filterAction !== 'all' && o.action !== filterAction) return false
      if (filterMomentum === 'momentum' && !o.is_momentum_pick) return false
      return true
    })
  }, [data, filterClass, filterAction, filterMomentum])

  const classOptions = useMemo(
    () => [
      { value: 'all' as const, label: t('opportunities.all') },
      ...(Object.keys(asset) as AssetClass[]).map((k) => ({ value: k, label: asset[k] })),
    ],
    [t, asset],
  )

  const signalOptions = useMemo(
    () => [
      { value: 'all' as const, label: t('opportunities.all') },
      ...(Object.keys(signal) as SignalAction[]).map((k) => ({ value: k, label: signal[k] })),
    ],
    [t, signal],
  )

  const momentumOptions = useMemo(
    () => [
      { value: 'all' as const, label: t('opportunities.all') },
      { value: 'momentum' as const, label: t('opportunities.momentumFilter') },
    ],
    [t],
  )

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (loading && !data) return <Loading message={t('layout.loading')} />
  if (!data) return null

  return (
    <div>
      <div className="filter-section">
        <div className="filter-label">{t('opportunities.filterClass')}</div>
        <FilterChips options={classOptions} value={filterClass} onChange={setFilterClass} />
      </div>
      <div className="filter-section">
        <div className="filter-label">{t('opportunities.filterSignal')}</div>
        <FilterChips options={signalOptions} value={filterAction} onChange={setFilterAction} />
      </div>
      <div className="filter-section">
        <div className="filter-label">{t('opportunities.filterMomentum')}</div>
        <FilterChips options={momentumOptions} value={filterMomentum} onChange={setFilterMomentum} />
      </div>
      <div className="filter-count-bar">{t('opportunities.count', { n: filtered.length })}</div>

      {filtered.length === 0 ? (
        <p className="empty-state">{t('opportunities.empty')}</p>
      ) : (
        <div className="opportunities-grid">
          {filtered.map((opp) => (
            <OpportunityCard key={`${opp.symbol}-${opp.created_at}`} opp={opp} />
          ))}
        </div>
      )}
    </div>
  )
}
