import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PortfolioSummary, usePaperPortfolio } from '../components/PaperTrading'
import { ErrorState } from '../components/Loading'
import { closePaperPosition, resetPaperPortfolio } from '../api'
import { formatPln } from '../utils/format'

function formatOpenedAt(iso?: string): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString('pl-PL')
}

export function PortfolioPage() {
  const { portfolio, loading, error, reload } = usePaperPortfolio()
  const [resetting, setResetting] = useState(false)
  const [closingSymbol, setClosingSymbol] = useState<string | null>(null)

  const handleClosePosition = async (symbol: string, quantity: number, isShort?: boolean) => {
    const label = isShort ? 'short' : 'long'
    if (!confirm(`Zamknąć całą pozycję ${label} na ${symbol} (${Math.abs(quantity)} szt.)?`)) return
    setClosingSymbol(symbol)
    try {
      await closePaperPosition(symbol)
      await reload()
    } catch (e) {
      alert((e as Error).message || 'Nie udało się zamknąć pozycji')
    } finally {
      setClosingSymbol(null)
    }
  }

  const handleReset = async () => {
    if (!confirm('Reset portfela do 1 000 000 PLN?')) return
    setResetting(true)
    try {
      await resetPaperPortfolio()
      await reload()
    } finally {
      setResetting(false)
    }
  }

  if (loading && !portfolio) return <div className="page-loading">Ładowanie portfela…</div>
  if (error && !portfolio) return <ErrorState message={error} onRetry={reload} />
  if (!portfolio) return null

  return (
    <div className="portfolio-page">
      <div className="info-banner">
        <h2>Paper trading</h2>
        <p>
          Wirtualne konto startowe <strong>1 000 000 PLN</strong>. Kupuj i sprzedawaj wszystkie 246
          instrumentów po cenach live. Prowizja 0,1%. Możesz sprzedawać bez posiadania akcji (short).
          Handel symulowany — bez realnych pieniędzy.
        </p>
      </div>

      <PortfolioSummary portfolio={portfolio} />

      <div className="section-header">
        <h3>Pozycje ({portfolio.positions_count})</h3>
        <button type="button" className="btn-link tap-target" onClick={handleReset} disabled={resetting}>
          Reset konta
        </button>
      </div>

      {portfolio.positions.length === 0 ? (
        <p className="empty-state">Brak otwartych pozycji. Kup instrument na stronie Rynki.</p>
      ) : (
        <div className="positions-list">
          {portfolio.positions.map((p) => (
            <div key={p.symbol} className="position-row">
              <Link
                to={`/instrument/${encodeURIComponent(p.symbol)}`}
                className="position-row-link tap-target"
              >
                <div className="position-main">
                  <strong>{p.symbol}</strong>
                  <span>{p.name}</span>
                  {formatOpenedAt(p.opened_at) && (
                    <span className="position-opened-at">Otwarto: {formatOpenedAt(p.opened_at)}</span>
                  )}
                </div>
                <div className="position-stats">
                  <span>
                    {p.is_short ? `SHORT ${Math.abs(p.quantity)} szt.` : `${p.quantity} szt.`}
                  </span>
                  <span>{formatPln(p.market_value_pln)}</span>
                  <span className={p.unrealized_pnl_pln >= 0 ? 'positive' : 'negative'}>
                    {p.unrealized_pnl_pln >= 0 ? '+' : ''}
                    {formatPln(p.unrealized_pnl_pln)} ({p.unrealized_pnl_pct}%)
                  </span>
                </div>
              </Link>
              <button
                type="button"
                className="btn-close-position btn-close-position-prominent tap-target"
                disabled={closingSymbol === p.symbol}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleClosePosition(p.symbol, p.quantity, p.is_short)
                }}
              >
                {closingSymbol === p.symbol ? 'Zamykanie…' : 'Zamknij'}
              </button>
            </div>
          ))}
        </div>
      )}

      <h3 className="section-title">Ostatnie transakcje</h3>
      {portfolio.recent_trades.length === 0 ? (
        <p className="empty-state">Brak transakcji.</p>
      ) : (
        <div className="trades-list">
          {portfolio.recent_trades.map((t) => (
            <div key={t.id} className="trade-row">
              <span className={`side-${t.side}`}>{t.side === 'buy' ? 'KUP' : 'SPRZEDAJ'}</span>
              <span>{t.symbol}</span>
              <span>{t.quantity}</span>
              <span>{formatPln(t.total_pln)}</span>
              <span className="trade-time">{new Date(t.created_at).toLocaleString('pl-PL')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
