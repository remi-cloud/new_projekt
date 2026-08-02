import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import AssetsTable from '../components/AssetsTable'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { fetchMarketStatus, fetchMarkets, MarketStatus } from '../api'
import { MarketsResponse } from '../types'

type RegionFilter = string

const POLL_MS = 12_000

export default function MarketsPage() {
  const [data, setData] = useState<MarketsResponse | null>(null)
  const [status, setStatus] = useState<MarketStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [region, setRegion] = useState<RegionFilter>('all')
  const hasData = useRef(false)

  const load = useCallback(async (nextRegion: RegionFilter, refresh = false) => {
    try {
      if (refresh) setRefreshing(true)
      else if (!hasData.current) setLoading(true)
      const [markets, probe] = await Promise.all([
        fetchMarkets(nextRegion, refresh),
        fetchMarketStatus().catch(() => null),
      ])
      setData(markets)
      hasData.current = true
      if (probe) setStatus(probe)
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

  useEffect(() => {
    const id = window.setInterval(() => {
      void load(region, false)
    }, POLL_MS)
    return () => window.clearInterval(id)
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

  const connected = Boolean(status?.connected) || (data?.live_count ?? 0) > 0
  const providers = [
    status?.tradingview?.ok ? 'TV' : null,
    status?.yahoo?.ok ? 'YH' : null,
    status?.coingecko?.ok ? 'CG' : null,
  ]
    .filter(Boolean)
    .join('+') || '—'

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
            Notowania na żywo (TradingView → Yahoo → CoinGecko). Auto-odświeżanie co 12 s.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={refreshing}
          onClick={() => void load(region, true)}
        >
          {refreshing ? 'Odświeżam…' : 'Odśwież teraz'}
        </button>
      </div>

      <div className={`markets-status ${connected && data.live_count > 0 ? 'ok' : 'bad'}`}>
        <strong>
          {connected ? 'POŁĄCZONO' : 'BRAK POŁĄCZENIA'} · {data.live_count}/{data.count} live
        </strong>
        <span>
          źródła {providers} · auto {POLL_MS / 1000}s ·{' '}
          {new Date(data.generated_at).toLocaleTimeString('pl-PL')}
        </span>
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
