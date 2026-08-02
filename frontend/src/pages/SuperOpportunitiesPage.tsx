import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchSuperOpportunities, fetchSuperOpportunity, triggerScan } from '../api'
import LiquidationHeatmapBar from '../components/LiquidationHeatmap'
import LoadingState, { ErrorState } from '../components/LoadingState'
import SignalTag from '../components/SignalTag'
import { ASSET_LABELS, formatPrice } from '../lib/labels'
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
  const [onlySuper, setOnlySuper] = useState(true)
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

  // Deep-link: URL symbol is source of truth; fetch solo detail if missing from list
  useEffect(() => {
    if (!data || !selectedSymbol) {
      setDetail(null)
      return
    }
    const inList = data.items.find(
      (i) => i.symbol.toUpperCase() === selectedSymbol.toUpperCase(),
    )
    if (inList) {
      setDetail(inList)
      if (!inList.is_super) setOnlySuper(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const one = await fetchSuperOpportunity(selectedSymbol)
        if (!cancelled) {
          setDetail(one)
          setOnlySuper(false)
        }
      } catch (e) {
        if (!cancelled) {
          setDetail(null)
          setError(e instanceof Error ? e.message : 'Brak pozycji dla symbolu')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [data, selectedSymbol])

  // No symbol in URL → open first visible item
  useEffect(() => {
    if (!data || selectedSymbol) return
    const pool = onlySuper && data.supers.length ? data.supers : data.items
    const first = pool[0]
    if (first) navigate(positionPath(first.symbol), { replace: true })
  }, [data, selectedSymbol, onlySuper, navigate])

  const list = useMemo(() => {
    if (!data) return []
    const pool = onlySuper ? data.supers : data.items
    // Always keep the deep-linked symbol visible in the ranking
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
  }, [data, onlySuper, selectedSymbol, detail])

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
            Pełna pozycja: bid/ask, poziomy IN/SL/TP oraz heatmapa liq 3D z głębią (HiDPI).
            Przeciągnij mapę, żeby obrócić. Linki z Okazji / Rynków / Watchlisty / Historii.
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
          <strong>{data.count}</strong>
          <span>kandydatów</span>
        </div>
        <div className="home-stat">
          <strong>
            {data.generated_at ? new Date(data.generated_at).toLocaleTimeString('pl-PL') : '—'}
          </strong>
          <span>ostatnie wyliczenie</span>
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
                  <SignalTag action={item.action} />
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
          <p className="page-lead">{item.rationale}</p>
        </div>
        <div className="super-score-badge">
          <span>SUPER SCORE</span>
          <strong>{item.super_score}</strong>
          {item.is_super && <em>SUPER</em>}
        </div>
      </div>

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
          <span>Strona</span>
          <strong>{levels.side}</strong>
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
