import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchSuperOpportunities, fetchSuperOpportunity, triggerScan } from '../api'
import { AskAgentButton } from '../components/AskAgentButton'
import { CommunityActions } from '../components/CommunityActions'
import LiquidationHeatmapBar from '../components/LiquidationHeatmap'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { QuickTradeButtons } from '../components/QuickTradeButtons'
import SignalTag from '../components/SignalTag'
import SingularityTool from '../components/SingularityTool'
import { ASSET_LABELS, formatDirection, formatPrice } from '../lib/labels'
import { positionPath } from '../lib/routes'
import { SuperOpportunity, SuperOpportunitiesResponse } from '../types'

async function mapPool<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const out: R[] = new Array(items.length)
  let i = 0
  async function worker() {
    while (i < items.length) {
      const idx = i++
      out[idx] = await fn(items[idx])
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, () => worker()))
  return out
}

function heatmapHasData(hm: SuperOpportunity['heatmap'] | undefined | null): boolean {
  if (!hm) return false
  const cols = hm.columns?.length ?? 0
  const bins = hm.bins?.length ?? 0
  return cols > 0 || bins > 0
}

export default function SuperOpportunitiesPage() {
  const { symbol: routeSymbol } = useParams()
  const focusSymbol = routeSymbol ? decodeURIComponent(routeSymbol) : null

  const [data, setData] = useState<SuperOpportunitiesResponse | null>(null)
  const [bySymbol, setBySymbol] = useState<Record<string, SuperOpportunity>>({})
  const [loading, setLoading] = useState(true)
  const [hydrating, setHydrating] = useState(false)
  const [hydrateFailed, setHydrateFailed] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [onlySuper, setOnlySuper] = useState(false)
  const [sideFilter, setSideFilter] = useState<'all' | 'long' | 'short'>('all')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      setLoading(true)
      const res = await fetchSuperOpportunities(0)
      setData(res)
      // Seed with list payloads (bins preview) so heatmaps show immediately
      const seed: Record<string, SuperOpportunity> = {}
      for (const item of res.items) seed[item.symbol.toUpperCase()] = item
      setBySymbol(seed)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się pobrać superokazji')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Hydrate FULL 3D heatmap for every position (like original detail, for all cards)
  useEffect(() => {
    if (!data?.items?.length) return
    let cancelled = false
    ;(async () => {
      setHydrating(true)
      setHydrateFailed({})
      try {
        const results = await mapPool(data.items, 4, async (item) => {
          try {
            const full = await fetchSuperOpportunity(item.symbol)
            return { ok: true as const, item, full }
          } catch {
            return { ok: false as const, item }
          }
        })
        if (cancelled) return
        const next: Record<string, SuperOpportunity> = {}
        const failed: Record<string, boolean> = {}
        for (const row of results) {
          const key = row.item.symbol.toUpperCase()
          if (!row.ok) {
            failed[key] = true
            continue
          }
          const full = row.full
          if (!full) {
            failed[key] = true
            continue
          }
          // Keep seed (bins preview) unless detail actually has drawable heatmap data.
          if (heatmapHasData(full.heatmap)) {
            next[key] = full
          } else {
            failed[key] = true
          }
        }
        setBySymbol((prev) => ({ ...prev, ...next }))
        setHydrateFailed(failed)
      } finally {
        if (!cancelled) setHydrating(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [data])

  const list = useMemo(() => {
    if (!data) return []
    let pool = onlySuper && data.supers.length > 0 ? data.supers : data.items
    if (sideFilter !== 'all') {
      pool = pool.filter((i) => i.levels.side === sideFilter)
    }
    return pool.map((item) => bySymbol[item.symbol.toUpperCase()] ?? item)
  }, [data, onlySuper, sideFilter, bySymbol])

  useEffect(() => {
    if (!focusSymbol || !list.length) return
    const el = document.getElementById(`pozycja-${focusSymbol}`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [focusSymbol, list])

  if (loading) {
    return <LoadingState message="Liczenie superokazji (bid/ask + heatmapa liq)…" />
  }
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  return (
    <div className="page super-page">
      <div className="page-header">
        <div>
          <h1>Superokazje</h1>
          <p className="page-lead">
            Heatmapa likwidacji jest na <strong>każdej</strong> pozycji (IN / SL / TP + liq).{' '}
            {hydrating ? 'Dociąganie pełnej mapy 3D…' : null}
            Singularity: <Link to="/narzedzia">Narzędzia</Link>.
          </p>
        </div>
        <div className="page-actions">
          <label className="check-row">
            <input
              type="checkbox"
              checked={onlySuper}
              onChange={(e) => setOnlySuper(e.target.checked)}
            />
            Tylko SUPER (≥72)
          </label>
          <div className="filter-chips">
            {(
              [
                ['all', 'Wszystkie'],
                ['long', 'LONG'],
                ['short', 'SHORT'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={`chip${sideFilter === id ? ' active' : ''}`}
                onClick={() => setSideFilter(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            className="btn btn-ghost"
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await triggerScan()
                await load()
              } finally {
                setBusy(false)
              }
            }}
          >
            Przeskanuj
          </button>
          <button className="btn btn-primary" type="button" onClick={load} disabled={busy}>
            Odśwież obliczenia
          </button>
        </div>
      </div>

      {error && <p className="inline-error">{error}</p>}

      <div className="super-stats">
        <div className="home-stat">
          <strong>{data.super_count}</strong>
          <span>superokazji</span>
        </div>
        <div className="home-stat">
          <strong className="pos">{data.long_count ?? '—'}</strong>
          <span>LONG</span>
        </div>
        <div className="home-stat">
          <strong className="neg">{data.short_count ?? '—'}</strong>
          <span>SHORT</span>
        </div>
        <div className="home-stat">
          <strong>{list.length}</strong>
          <span>pozycji z heatmapą</span>
        </div>
      </div>

      {list.length === 0 ? (
        <p className="empty">Brak pozycji. Odznacz filtr SUPER albo uruchom skan.</p>
      ) : (
        <div className="super-feed">
          {list.map((item) => (
            <PositionCard
              key={item.symbol}
              item={item}
              focused={focusSymbol?.toUpperCase() === item.symbol.toUpperCase()}
              hydrateFailed={!!hydrateFailed[item.symbol.toUpperCase()]}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function PositionCard({
  item,
  focused,
  hydrateFailed,
}: {
  item: SuperOpportunity
  focused: boolean
  hydrateFailed?: boolean
}) {
  const { levels } = item
  return (
    <article
      id={`pozycja-${item.symbol}`}
      className={`super-card super-feed-card${focused ? ' active' : ''}${item.is_super ? ' is-super' : ''}`}
    >
      <div className="super-card-head">
        <div>
          <h2>
            <Link to={positionPath(item.symbol)}>
              {item.name} <span className="cell-sub">{item.symbol}</span>
            </Link>
          </h2>
          <div className="super-dir-row">
            <SignalTag action={item.action} />
            <span className={`tag ${item.asset_class}`}>{ASSET_LABELS[item.asset_class]}</span>
            <span className="cell-sub">{formatDirection(levels.side)}</span>
          </div>
          <p className="page-lead">{item.rationale}</p>
        </div>
        <div className="super-score-badge">
          <span>SUPER SCORE</span>
          <strong>{item.super_score}</strong>
          {item.is_super && <em>SUPER</em>}
          <div className="super-card-actions">
            <CommunityActions
              symbol={item.symbol}
              name={item.name}
              community={item.community}
              compact
            />
            <AskAgentButton
              mode="instrument"
              symbol={item.symbol}
              name={item.name}
              extra={item.rationale}
              compact
            />
          </div>
        </div>
      </div>

      <QuickTradeButtons symbol={item.symbol} compact />

      <SingularityTool ai={item.ai_signal} />

      {item.whale && item.whale.bias !== 'neutral' && (
        <div className={`whale-panel bias-${item.whale.bias}`}>
          <div className="whale-panel-head">
            <span className="whale-tag">WHALE</span>
            <strong>
              {item.whale.bias === 'accumulate' ? 'WEJŚCIE' : 'WYJŚCIE'}
            </strong>
            <em>{item.whale.strength.toFixed(0)}</em>
          </div>
          <p>{item.whale.summary}</p>
        </div>
      )}

      <div className="book-strip" aria-label="Bid Ask">
        <div className="super-grid">
          <div className="stat bid-stat">
            <div className="stat-label">Bid</div>
            <div className="stat-value">
              {item.bid != null ? formatPrice(item.bid, item.asset_class) : '—'}
            </div>
          </div>
          <div className="stat ask-stat">
            <div className="stat-label">Ask</div>
            <div className="stat-value">
              {item.ask != null ? formatPrice(item.ask, item.asset_class) : '—'}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Spread</div>
            <div className="stat-value">
              {item.spread_pct != null ? `${item.spread_pct.toFixed(3)}%` : '—'}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Mid</div>
            <div className="stat-value">{formatPrice(item.price, item.asset_class)}</div>
          </div>
        </div>
        {item.bid != null && item.ask != null && (
          <div className="bidask-compare">
            <div className="bidask-bar" aria-hidden>
              <div className="bidask-bid" style={{ flex: 1 }} />
              <div className="bidask-spread" />
              <div className="bidask-ask" style={{ flex: 1 }} />
            </div>
            <div className="bidask-labels">
              <span>BID {formatPrice(item.bid, item.asset_class)}</span>
              <span>
                spread {item.spread_pct != null ? `${item.spread_pct.toFixed(3)}%` : '—'}
              </span>
              <span>ASK {formatPrice(item.ask, item.asset_class)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="levels-grid">
        <div>
          <span>IN</span>
          <strong>{levels.entry}</strong>
        </div>
        <div>
          <span>SL</span>
          <strong className="neg">{levels.stop_loss}</strong>
        </div>
        <div>
          <span>TP1</span>
          <strong className="pos">{levels.take_profit_1}</strong>
        </div>
        <div>
          <span>TP2</span>
          <strong className="pos">{levels.take_profit_2}</strong>
        </div>
        <div>
          <span>R:R</span>
          <strong>{levels.risk_reward}</strong>
        </div>
        <div>
          <span>Kierunek</span>
          <strong className={`signal-tag signal-${levels.side}`}>{formatDirection(levels.side)}</strong>
        </div>
      </div>

      <h3 className="mini-title">Heatmapa likwidacji · {item.symbol}</h3>
      {hydrateFailed && (
        <p className="inline-error" style={{ marginBottom: 8 }}>
          Pełna mapa 3D nie dociągnęła się — pokazuję podgląd bins (odśwież kartę / skan).
        </p>
      )}
      <LiquidationHeatmapBar
        heatmap={item.heatmap}
        entry={levels.entry}
        stop={levels.stop_loss}
        tp1={levels.take_profit_1}
        tp2={levels.take_profit_2}
        prediction={item.prediction}
      />

      {item.reasons?.length > 0 && (
        <>
          <h3 className="mini-title">Dlaczego ta ocena</h3>
          <ul className="reason-list">
            {item.reasons.slice(0, 8).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </>
      )}
    </article>
  )
}
