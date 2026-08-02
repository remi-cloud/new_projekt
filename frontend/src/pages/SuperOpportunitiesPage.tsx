import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchSuperOpportunities, fetchSuperOpportunity, triggerScan } from '../api'
import LiquidationHeatmapBar from '../components/LiquidationHeatmap'
import LoadingState, { ErrorState } from '../components/LoadingState'
import SignalTag from '../components/SignalTag'
import SingularityTool from '../components/SingularityTool'
import { ASSET_LABELS, formatDirection, formatPrice } from '../lib/labels'
import { positionPath } from '../lib/routes'
import { SuperOpportunity, SuperOpportunitiesResponse } from '../types'

export default function SuperOpportunitiesPage() {
  const { symbol: routeSymbol } = useParams()
  const navigate = useNavigate()
  const selectedSymbol = routeSymbol ? decodeURIComponent(routeSymbol) : null

  const [data, setData] = useState<SuperOpportunitiesResponse | null>(null)
  const [detail, setDetail] = useState<SuperOpportunity | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [onlySuper, setOnlySuper] = useState(false)
  const [sideFilter, setSideFilter] = useState<'all' | 'long' | 'short'>('all')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const res = await fetchSuperOpportunities(0)
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się pobrać superokazji')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Always load full 3D heatmap for the selected symbol (list is lightweight preview).
  useEffect(() => {
    if (!selectedSymbol) {
      setDetail(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const one = await fetchSuperOpportunity(selectedSymbol)
        if (!cancelled) {
          setDetail(one)
          if (!one.is_super) setOnlySuper(false)
        }
      } catch (e) {
        if (!cancelled) {
          // Fall back to list row if detail endpoint fails
          const inList = data?.items.find(
            (i) => i.symbol.toUpperCase() === selectedSymbol.toUpperCase(),
          )
          if (inList) setDetail(inList)
          else {
            setDetail(null)
            setError(e instanceof Error ? e.message : 'Brak pozycji dla symbolu')
          }
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedSymbol, data])

  // No symbol in URL → open first visible item
  useEffect(() => {
    if (!data || selectedSymbol) return
    const pool = onlySuper && data.supers.length ? data.supers : data.items
    const first = pool[0]
    if (first) navigate(positionPath(first.symbol), { replace: true })
  }, [data, selectedSymbol, onlySuper, navigate])

  const list = useMemo(() => {
    if (!data) return []
    // Never show an empty ranking when SUPER filter has no hits
    let pool =
      onlySuper && data.supers.length > 0
        ? data.supers
        : data.items
    if (sideFilter !== 'all') {
      pool = pool.filter((i) => i.levels.side === sideFilter)
    }
    if (
      selectedSymbol &&
      !pool.some((i) => i.symbol.toUpperCase() === selectedSymbol.toUpperCase())
    ) {
      const extra =
        detail && detail.symbol.toUpperCase() === selectedSymbol.toUpperCase()
          ? detail
          : data.items.find((i) => i.symbol.toUpperCase() === selectedSymbol.toUpperCase())
      if (extra) return [extra, ...pool]
    }
    return pool
  }, [data, onlySuper, sideFilter, selectedSymbol, detail])

  const active =
    detail ??
    list.find((i) => i.symbol.toUpperCase() === (selectedSymbol ?? '').toUpperCase()) ??
    list[0] ??
    null

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
            Pełna pozycja: bid/ask, poziomy IN/SL/TP, heatmapa liq 3D. Singularity jest w{' '}
            <Link to="/narzedzia">Narzędziach</Link> — nie na banerze.
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
          <strong>{data.count}</strong>
          <span>kandydatów</span>
        </div>
      </div>

      <div className="super-layout">
        <aside className="super-list">
          <h2 className="section-title">
            Ranking
            <span className="count">{list.length}</span>
          </h2>
          {list.length === 0 ? (
            <p className="empty">Brak pozycji spełniających próg. Odznacz filtr SUPER.</p>
          ) : (
            list.map((item) => (
              <Link
                key={item.symbol}
                to={positionPath(item.symbol)}
                className={`super-list-item${active?.symbol === item.symbol ? ' active' : ''}${item.is_super ? ' super' : ''}`}
              >
                <div className="super-list-top">
                  <strong>{item.symbol}</strong>
                  {item.ai_signal ? (
                    <span className={`ai-mini-tag ai-mini-${item.ai_signal.signal}`}>
                      {item.ai_signal.label}
                    </span>
                  ) : (
                    <SignalTag action={item.action} />
                  )}
                </div>
                <div className="super-list-meta">
                  <span className={`tag ${item.asset_class}`}>{ASSET_LABELS[item.asset_class]}</span>
                  <span className="super-score">{item.super_score}</span>
                </div>
              </Link>
            ))
          )}
        </aside>

        <section className="super-detail">
          {active ? (
            <SuperDetail item={active} />
          ) : (
            <p className="empty">
              Brak pozycji. Uruchom skan albo otwórz instrument z{' '}
              <Link to="/okazje">Okazji</Link> / <Link to="/rynki">Rynków</Link>.
            </p>
          )}
        </section>
      </div>
    </div>
  )
}

function SuperDetail({ item }: { item: SuperOpportunity }) {
  const { levels } = item
  return (
    <div className="super-card" id={`pozycja-${item.symbol}`}>
      <div className="super-card-head">
        <div>
          <h2>
            {item.name} <span className="cell-sub">{item.symbol}</span>
          </h2>
          <div className="super-dir-row">
            <SignalTag action={item.action} />
            <span className="cell-sub">kierunek pozycji</span>
          </div>
          <p className="page-lead">{item.rationale}</p>
        </div>
        <div className="super-score-badge">
          <span>SUPER SCORE</span>
          <strong>{item.super_score}</strong>
          {item.is_super && <em>SUPER</em>}
        </div>
      </div>

      <SingularityTool ai={item.ai_signal} />

      <div className="super-grid">
        <div className="stat">
          <div className="stat-label">Bid</div>
          <div className="stat-value">
            {item.bid != null ? formatPrice(item.bid, item.asset_class) : '—'}
          </div>
        </div>
        <div className="stat">
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
          <div className="stat-label">Mid / model</div>
          <div className="stat-value">
            {formatPrice(item.price, item.asset_class)} · {item.cycle_confidence}%
          </div>
        </div>
      </div>

      <div className="bidask-compare">
        <div className="bidask-bar">
          <div className="bidask-bid" style={{ flex: item.bid ?? 1 }} />
          <div className="bidask-spread" />
          <div className="bidask-ask" style={{ flex: item.ask ?? 1 }} />
        </div>
        <div className="bidask-labels">
          <span>BID {item.bid ?? '—'}</span>
          <span>{item.book_source ?? 'brak książki'}</span>
          <span>ASK {item.ask ?? '—'}</span>
        </div>
      </div>

      <h3 className="mini-title">Poziomy wejścia / wyjścia</h3>
      <div className="levels-grid" id="levels-anchors">
        <div data-anchor="side">
          <span>Kierunek</span>
          <strong className={`signal-tag signal-${levels.side}`}>{formatDirection(levels.side)}</strong>
        </div>
        <div data-anchor="entry" className="level-hot">
          <span>Wejście · IN</span>
          <strong>{levels.entry}</strong>
        </div>
        <div data-anchor="stop" className="level-hot neg-box">
          <span>Stop · SL</span>
          <strong className="neg">{levels.stop_loss}</strong>
        </div>
        <div data-anchor="tp1" className="level-hot">
          <span>TP1</span>
          <strong className="pos">{levels.take_profit_1}</strong>
        </div>
        <div data-anchor="tp2" className="level-hot">
          <span>TP2</span>
          <strong className="pos">{levels.take_profit_2}</strong>
        </div>
        <div data-anchor="rr">
          <span>R:R</span>
          <strong>{levels.risk_reward}</strong>
        </div>
      </div>
      <p className="opp-rationale">{levels.note}</p>

      <div className="path-bridge" aria-hidden>
        <span className="path-bridge-dot in">IN</span>
        <span className="path-bridge-line" />
        <span className="path-bridge-dot tp">TP</span>
        <span className="path-bridge-line ai" />
        <span className="path-bridge-dot liq">LIQ</span>
        <span className="path-bridge-caption">
          {item.prediction
            ? `AI łączy pozycję z ${item.prediction.target_side}-liq @ ${item.prediction.target_price}`
            : 'Ścieżka pozycja → liq'}
        </span>
      </div>

      <h3 className="mini-title">Heatmapa likwidacji 3D + ścieżka AI</h3>
      <LiquidationHeatmapBar
        heatmap={item.heatmap}
        entry={levels.entry}
        stop={levels.stop_loss}
        tp1={levels.take_profit_1}
        tp2={levels.take_profit_2}
        prediction={item.prediction}
      />

      <h3 className="mini-title">Dlaczego ta ocena</h3>
      <ul className="reason-list">
        {item.reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </div>
  )
}
