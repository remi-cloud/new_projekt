import { useMemo, useState } from 'react'
import FilterBar from '../components/FilterBar'
import LoadingState, { ErrorState } from '../components/LoadingState'
import OpportunityCard from '../components/OpportunityCard'
import { useDashboard } from '../hooks/useDashboard'
import { AssetClass, SignalAction } from '../types'

export default function OpportunitiesPage() {
  const { data, loading, scanning, error, load, scan } = useDashboard()
  const [assetClass, setAssetClass] = useState<AssetClass | 'all'>('all')
  const [action, setAction] = useState<SignalAction | 'all'>('all')

  const filtered = useMemo(() => {
    if (!data) return []
    return data.opportunities.filter((o) => {
      if (assetClass !== 'all' && o.asset_class !== assetClass) return false
      if (action !== 'all' && o.action !== action) return false
      return true
    })
  }, [data, assetClass, action])

  if (loading) return <LoadingState />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Okazje tradingowe</h1>
          <p className="page-lead">
            Kliknij kartę — otwiera pełną pozycję jak w Superokazjach (bid/ask, poziomy, heatmapa).
          </p>
        </div>
        <button className="btn btn-primary" onClick={scan} disabled={scanning} type="button">
          {scanning ? 'Skanowanie…' : 'Odśwież skan'}
        </button>
      </div>

      <FilterBar
        assetClass={assetClass}
        action={action}
        onAssetClass={setAssetClass}
        onAction={setAction}
      />

      <h2 className="section-title">
        Wyniki
        <span className="count">{filtered.length}</span>
      </h2>

      {filtered.length === 0 ? (
        <p className="empty">Brak okazji dla wybranych filtrów.</p>
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
