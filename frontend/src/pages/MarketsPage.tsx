import { useMemo, useState } from 'react'
import { FilterChips } from '../components/FilterChips'
import { MarketAssessmentCard, MarketSummaryBanner } from '../components/MarketAssessmentCard'
import { ErrorState } from '../components/Loading'
import { ASSET_LABELS, REGION_LABELS, SIGNAL_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'
import { AssetClass, Region, SignalAction } from '../types'

export function MarketsPage() {
  const { data, error, reload } = useDashboardContext()
  const [filterClass, setFilterClass] = useState<AssetClass | 'all'>('all')
  const [filterRegion, setFilterRegion] = useState<Region | 'all'>('all')
  const [filterSignal, setFilterSignal] = useState<SignalAction | 'all'>('all')

  const filtered = useMemo(() => {
    if (!data?.market_assessments) return []
    return data.market_assessments.filter((a) => {
      if (filterClass !== 'all' && a.asset_class !== filterClass) return false
      if (filterRegion !== 'all' && a.region !== filterRegion) return false
      if (filterSignal !== 'all' && a.signal !== filterSignal) return false
      return true
    })
  }, [data, filterClass, filterRegion, filterSignal])

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  const classOptions = [
    { value: 'all' as const, label: 'Wszystkie' },
    ...(Object.keys(ASSET_LABELS) as AssetClass[]).map((k) => ({
      value: k,
      label: ASSET_LABELS[k],
    })),
  ]

  const regionOptions = [
    { value: 'all' as const, label: 'Świat' },
    ...(Object.keys(REGION_LABELS) as Region[]).map((k) => ({
      value: k,
      label: REGION_LABELS[k],
    })),
  ]

  const signalOptions = [
    { value: 'all' as const, label: 'Wszystkie' },
    ...(Object.keys(SIGNAL_LABELS) as SignalAction[]).map((k) => ({
      value: k,
      label: SIGNAL_LABELS[k],
    })),
  ]

  return (
    <div className="markets-page">
      {data.market_summary && <MarketSummaryBanner summary={data.market_summary} />}

      <div className="filter-section">
        <div className="filter-label">Region</div>
        <FilterChips options={regionOptions} value={filterRegion} onChange={setFilterRegion} />
      </div>
      <div className="filter-section">
        <div className="filter-label">Klasa aktywów</div>
        <FilterChips options={classOptions} value={filterClass} onChange={setFilterClass} />
      </div>
      <div className="filter-section">
        <div className="filter-label">Sygnał</div>
        <FilterChips options={signalOptions} value={filterSignal} onChange={setFilterSignal} />
      </div>

      <div className="filter-count-bar">{filtered.length} instrumentów</div>

      <div className="markets-list">
        {filtered.map((item) => (
          <MarketAssessmentCard key={item.symbol} item={item} />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="empty-state">Brak instrumentów dla wybranych filtrów.</p>
      )}
    </div>
  )
}
