import { useCallback, useEffect, useState } from 'react'
import { fetchSuperOpportunities, triggerScan } from '../api'
import LiquidationHeatmapBar from '../components/LiquidationHeatmap'
import LoadingState, { ErrorState } from '../components/LoadingState'
import SignalTag from '../components/SignalTag'
import { ASSET_LABELS, formatPrice } from '../lib/labels'
import { SuperOpportunity, SuperOpportunitiesResponse } from '../types'

export default function SuperOpportunitiesPage() {
  const [data, setData] = useState<SuperOpportunitiesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [onlySuper, setOnlySuper] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const res = await fetchSuperOpportunities(0)
      setData(res)
      setSelected((prev) => prev ?? res.items[0]?.symbol ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się pobrać superokazji')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return <LoadingState message="Liczenie superokazji (bid/ask + heatmapa liq)…" />
  }
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  const list = onlySuper ? data.supers : data.items
  const active = list.find((i) => i.symbol === selected) ?? list[0] ?? data.items[0]

  return (
    <div className="page super-page">
      <div className="page-header">
        <div>
          <h1>Superokazje</h1>
          <p className="page-lead">
            Osobne okno: cykl + porównanie bid/ask + poziomy wejścia/wyjścia + pozioma heatmapa
            likwidacji (zieleń = long liq, czerwień = short liq).
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
          <strong>{data.generated_at ? new Date(data.generated_at).toLocaleTimeString('pl-PL') : '—'}</strong>
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
              <button
                key={item.symbol}
                type="button"
                className={`super-list-item${active?.symbol === item.symbol ? ' active' : ''}${item.is_super ? ' super' : ''}`}
                onClick={() => setSelected(item.symbol)}
              >
                <div className="super-list-top">
                  <strong>{item.symbol}</strong>
                  <SignalTag action={item.action} />
                </div>
                <div className="super-list-meta">
                  <span className={`tag ${item.asset_class}`}>{ASSET_LABELS[item.asset_class]}</span>
                  <span className="super-score">{item.super_score}</span>
                </div>
              </button>
            ))
          )}
        </aside>

        <section className="super-detail">
          {active ? <SuperDetail item={active} /> : <p className="empty">Wybierz instrument.</p>}
        </section>
      </div>
    </div>
  )
}

function SuperDetail({ item }: { item: SuperOpportunity }) {
  const { levels } = item
  return (
    <div className="super-card">
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
          <div className="stat-label">Mid / cykl</div>
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
      <div className="levels-grid">
        <div><span>Strona</span><strong>{levels.side}</strong></div>
        <div><span>Wejście</span><strong>{levels.entry}</strong></div>
        <div><span>Stop</span><strong className="neg">{levels.stop_loss}</strong></div>
        <div><span>TP1</span><strong className="pos">{levels.take_profit_1}</strong></div>
        <div><span>TP2</span><strong className="pos">{levels.take_profit_2}</strong></div>
        <div><span>R:R</span><strong>{levels.risk_reward}</strong></div>
      </div>
      <p className="opp-rationale">{levels.note}</p>

      <h3 className="mini-title">Heatmapa likwidacji (pozioma)</h3>
      <LiquidationHeatmapBar
        heatmap={item.heatmap}
        entry={levels.entry}
        stop={levels.stop_loss}
        tp1={levels.take_profit_1}
        tp2={levels.take_profit_2}
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
