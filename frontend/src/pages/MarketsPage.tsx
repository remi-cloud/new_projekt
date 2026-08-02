import { useCallback, useEffect, useMemo, useState } from 'react'
import AssetsTable from '../components/AssetsTable'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { fetchMarkets } from '../api'
import { MarketsResponse } from '../types'

type RegionFilter = string

export default function MarketsPage() {
  const [data, setData] = useState<MarketsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [region, setRegion] = useState<RegionFilter>('global')

  const load = useCallback(async (nextRegion: RegionFilter) => {
    try {
      setLoading(true)
      const markets = await fetchMarkets(nextRegion)
      setData(markets)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Błąd połączenia z API')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(region)
  }, [region, load])

  const chips = useMemo(() => {
    const regionRows = data?.regions ?? []
    const allCount = regionRows
      .filter((r) => r.id !== 'global')
      .reduce((n, r) => n + r.count, 0)
    const base = [{ id: 'all', label: 'Wszystkie', count: allCount }]
    const fromApi = regionRows.map((r) => ({
      id: r.id,
      label: r.label,
      count: r.count,
    }))
    return [...base, ...fromApi]
  }, [data])

  if (loading && !data) return <LoadingState />
  if (error && !data) return <ErrorState message={error} onRetry={() => load(region)} />
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Rynki</h1>
          <p className="page-lead">
            Azja, Rosja, Brazylia, Europa, EM — osobno od USA. Kliknij instrument, aby otworzyć pozycję.
          </p>
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <span className="filter-label">Region</span>
          <div className="filter-chips">
            {chips.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`chip${region === c.id ? ' active' : ''}`}
                onClick={() => setRegion(c.id)}
              >
                {c.label}
                <span className="chip-count">{c.count}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <h2 className="section-title">
        {region === 'global'
          ? 'Rynki globalne'
          : chips.find((c) => c.id === region)?.label ?? 'Instrumenty'}
        <span className="count">{data.count}</span>
        <span className="count-sub">{data.live_count} live</span>
      </h2>
      <AssetsTable assets={data.items} showRegion />
    </div>
  )
}
