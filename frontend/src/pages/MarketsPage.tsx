import { useCallback, useEffect, useMemo, useState } from 'react'
import AssetsTable from '../components/AssetsTable'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { fetchMarkets } from '../api'
import { MarketsResponse } from '../types'

type RegionFilter = string

export default function MarketsPage() {
  const [data, setData] = useState<MarketsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Default: full book — never hide USA/crypto/FX behind "global" filter
  const [region, setRegion] = useState<RegionFilter>('all')

  const load = useCallback(async (nextRegion: RegionFilter, refresh = false) => {
    try {
      if (refresh) setRefreshing(true)
      else setLoading(true)
      const markets = await fetchMarkets(nextRegion, refresh)
      setData(markets)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Błąd połączenia z API')
    } finally {
      setLoading(false)
      setRefreshing(false)
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
    const base = [{ id: 'all', label: 'Wszystkie', count: allCount || data?.count || 0 }]
    const fromApi = regionRows.map((r) => ({
      id: r.id,
      label: r.label,
      count: r.count,
    }))
    return [...base, ...fromApi]
  }, [data])

  if (loading && !data) return <LoadingState />
  if (error && !data) {
    return <ErrorState message={error} onRetry={() => load(region, true)} />
  }
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Rynki</h1>
          <p className="page-lead">
            Pełny katalog na żywo (Yahoo + TradingView). Azja, Rosja, Brazylia, Europa, USA, krypto, FX.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={refreshing}
          onClick={() => void load(region, true)}
        >
          {refreshing ? 'Odświeżam…' : 'Odśwież notowania'}
        </button>
      </div>

      {error && (
        <div className="inline-error" role="alert">
          {error} — pokazuję ostatnie dane.{' '}
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load(region, true)}>
            Spróbuj ponownie
          </button>
        </div>
      )}

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
        <span className="count-sub">{data.live_count} live / {data.global_count} global</span>
      </h2>

      {data.items.length === 0 ? (
        <div className="empty-block">
          <p>Brak instrumentów dla tego filtra.</p>
          <button type="button" className="btn btn-primary" onClick={() => setRegion('all')}>
            Pokaż wszystkie rynki
          </button>
        </div>
      ) : (
        <AssetsTable assets={data.items} showRegion showSource />
      )}
    </div>
  )
}
