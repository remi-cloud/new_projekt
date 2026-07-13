import { useMemo, useState } from 'react'
import { AssetsTable, filterAssets } from '../components/AssetsTable'
import { ErrorState } from '../components/Loading'
import { ASSET_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'
import { AssetClass } from '../types'

export function MarketsPage() {
  const { data, error, reload } = useDashboardContext()
  const [filterClass, setFilterClass] = useState<AssetClass | 'all'>('all')

  const filtered = useMemo(
    () => (data ? filterAssets(data.monitored_assets, filterClass) : []),
    [data, filterClass],
  )

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  return (
    <div>
      <div className="filters-bar">
        <select value={filterClass} onChange={(e) => setFilterClass(e.target.value as AssetClass | 'all')}>
          <option value="all">Wszystkie klasy ({data.monitored_assets.length})</option>
          {(Object.keys(ASSET_LABELS) as AssetClass[]).map((k) => (
            <option key={k} value={k}>{ASSET_LABELS[k]}</option>
          ))}
        </select>
      </div>
      <AssetsTable assets={filtered} />
    </div>
  )
}
