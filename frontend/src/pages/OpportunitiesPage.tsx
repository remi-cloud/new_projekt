import { useMemo, useState } from 'react'
import { OpportunityCard } from '../components/OpportunityCard'
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

  return (
    <div>
      <div className="filters-bar">
        <select value={filterClass} onChange={(e) => setFilterClass(e.target.value as AssetClass | 'all')}>
          <option value="all">Wszystkie klasy</option>
          {(Object.keys(ASSET_LABELS) as AssetClass[]).map((k) => (
            <option key={k} value={k}>{ASSET_LABELS[k]}</option>
          ))}
        </select>
        <select value={filterAction} onChange={(e) => setFilterAction(e.target.value as SignalAction | 'all')}>
          <option value="all">Wszystkie sygnały</option>
          {(Object.keys(SIGNAL_LABELS) as SignalAction[]).map((k) => (
            <option key={k} value={k}>{SIGNAL_LABELS[k]}</option>
          ))}
        </select>
        <span className="filter-count">{filtered.length} wyników</span>
      </div>

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
