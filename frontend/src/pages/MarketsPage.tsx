import { useMemo, useState } from 'react'
import AssetsTable from '../components/AssetsTable'
import FilterBar from '../components/FilterBar'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { useDashboard } from '../hooks/useDashboard'
import { AssetClass } from '../types'

export default function MarketsPage() {
  const { data, loading, error, load } = useDashboard()
  const [assetClass, setAssetClass] = useState<AssetClass | 'all'>('all')

  const filtered = useMemo(() => {
    if (!data) return []
    if (assetClass === 'all') return data.monitored_assets
    return data.monitored_assets.filter((a) => a.asset_class === assetClass)
  }, [data, assetClass])

  if (loading) return <LoadingState />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Rynki</h1>
          <p className="page-lead">
            Kliknij instrument lub „Otwórz”, aby wejść w pełną pozycję (Superokazje).
          </p>
        </div>
      </div>

      <FilterBar
        assetClass={assetClass}
        onAssetClass={setAssetClass}
        showAction={false}
      />

      <h2 className="section-title">
        Instrumenty
        <span className="count">{filtered.length}</span>
      </h2>
      <AssetsTable assets={filtered} />
    </div>
  )
}
