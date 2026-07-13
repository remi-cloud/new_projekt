import { useMemo, useState } from 'react'
import { OpportunityCard } from '../components/OpportunityCard'
import { FilterChips } from '../components/FilterChips'
import { ErrorState } from '../components/Loading'
import { ASSET_LABELS, SIGNAL_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'
import { AssetClass, SignalAction } from '../types'

export function OpportunitiesPage() {
  const { data, error, reload } = useDashboardContext()
  const [filterClass, setFilterClass] = useState<AssetClass | 'all'>('all')
  const [filterAction, setFilterAction] = useState<SignalAction | 'all'>('all')

  const filtered = useMemo(() => {
    if (!data) return []
    return data.opportunities.filter((o) => {
      if (filterClass !== 'all' && o.asset_class !== filterClass) return false
      if (filterAction !== 'all' && o.action !== filterAction) return false
      return true
    })
  }, [data, filterClass, filterAction])

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  const classOptions = [
    { value: 'all' as const, label: 'Wszystkie' },
    ...(Object.keys(ASSET_LABELS) as AssetClass[]).map((k) => ({ value: k, label: ASSET_LABELS[k] })),
  ]

  const signalOptions = [
    { value: 'all' as const, label: 'Wszystkie' },
    ...(Object.keys(SIGNAL_LABELS) as SignalAction[]).map((k) => ({ value: k, label: SIGNAL_LABELS[k] })),
  ]

  return (
    <div>
      <div className="filter-section">
        <div className="filter-label">Klasa</div>
        <FilterChips options={classOptions} value={filterClass} onChange={setFilterClass} />
      </div>
      <div className="filter-section">
        <div className="filter-label">Sygnał</div>
        <FilterChips options={signalOptions} value={filterAction} onChange={setFilterAction} />
      </div>
      <div className="filter-count-bar">{filtered.length} okazji</div>

      {filtered.length === 0 ? (
        <p className="empty-state">Brak okazji dla wybranych filtrów.</p>
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
