import { useMemo, useState } from 'react'
import { ConfidenceGuide } from '../components/ConfidenceGuide'
import { FilterChips } from '../components/FilterChips'
import { InstrumentPanel, MarketSummaryBanner } from '../components/MarketAssessmentCard'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { AssetClass, Region, SignalAction } from '../types'

export function MarketsPage() {
  const { data, error, reload, loading } = useDashboardContext()
  const { t } = useLocale()
  const { asset, region, signal } = useDomainLabels()
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

  const classOptions = useMemo(
    () => [
      { value: 'all' as const, label: t('markets.all') },
      ...(Object.keys(asset) as AssetClass[]).map((k) => ({ value: k, label: asset[k] })),
    ],
    [t, asset],
  )

  const regionOptions = useMemo(
    () => [
      { value: 'all' as const, label: t('markets.world') },
      ...(Object.keys(region) as Region[]).map((k) => ({ value: k, label: region[k] })),
    ],
    [t, region],
  )

  const signalOptions = useMemo(
    () => [
      { value: 'all' as const, label: t('markets.all') },
      ...(Object.keys(signal) as SignalAction[]).map((k) => ({ value: k, label: signal[k] })),
    ],
    [t, signal],
  )

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (loading && !data) return <Loading message={t('layout.loading')} />
  if (!data) return null

  return (
    <div className="markets-page">
      {data.market_summary && <MarketSummaryBanner summary={data.market_summary} />}

      <div className="filter-section">
        <div className="filter-label">{t('markets.filterRegion')}</div>
        <FilterChips options={regionOptions} value={filterRegion} onChange={setFilterRegion} />
      </div>
      <div className="filter-section">
        <div className="filter-label">{t('markets.filterClass')}</div>
        <FilterChips options={classOptions} value={filterClass} onChange={setFilterClass} />
      </div>
      <div className="filter-section">
        <div className="filter-label">{t('markets.filterSignal')}</div>
        <FilterChips options={signalOptions} value={filterSignal} onChange={setFilterSignal} />
      </div>

      <div className="filter-count-bar">{t('markets.count', { n: filtered.length })}</div>

      <ConfidenceGuide />

      <div className="markets-list">
        {filtered.map((item) => (
          <InstrumentPanel key={item.symbol} item={item} />
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="empty-state">{t('markets.empty')}</p>
      )}
    </div>
  )
}
