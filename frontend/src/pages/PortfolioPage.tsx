import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { PortfolioSummary, usePaperPortfolio } from '../components/PaperTrading'
import { OpenOrdersPanel } from '../components/OpenOrdersPanel'
import { PositionsSection } from '../components/PositionsSection'
import { ErrorState } from '../components/Loading'
import { resetPaperPortfolio, cancelPaperOrder, cancelAllPaperOrders } from '../api'
import { formatPln } from '../utils/format'

export function PortfolioPage() {
  const location = useLocation()
  const { portfolio, loading, error, reload } = usePaperPortfolio()
  const [positionsTab, setPositionsTab] = useState<'open' | 'closed'>('open')

  useEffect(() => {
    if (location.pathname === '/portfel') reload()
  }, [location.pathname, reload])

  const [resetting, setResetting] = useState(false)
  const [tradingSymbol, setTradingSymbol] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [cancellingAll, setCancellingAll] = useState(false)

  const handleTradeComplete = async (symbol: string) => {
    setTradingSymbol(symbol)
    try {
      await reload()
    } finally {
      setTradingSymbol(null)
    }
  }

  const handleCancelOrder = async (orderId: number) => {
    if (!confirm('Anulować zlecenie?')) return
    setCancellingId(orderId)
    try {
      await cancelPaperOrder(orderId)
      await reload()
    } catch (e) {
      alert((e as Error).message || 'Nie udało się anulować zlecenia')
    } finally {
      setCancellingId(null)
    }
  }

  const handleCancelAll = async () => {
    if (!confirm('Anulować wszystkie otwarte zlecenia?')) return
    setCancellingAll(true)
    try {
      await cancelAllPaperOrders()
      await reload()
    } catch (e) {
      alert((e as Error).message || 'Nie udało się anulować zleceń')
    } finally {
      setCancellingAll(false)
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

  const openOrders = portfolio.limit_orders ?? []
  const closedPositions = portfolio.closed_positions ?? []

  return (
    <div className="portfolio-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">Paper Trading · Simulated Account</span>
        <h2 className="page-headline">Portfel</h2>
        <p className="page-lead">
          Wirtualne konto startowe <strong>1 000 000 PLN</strong>. Otwarte i zamknięte pozycje, zlecenia limit/stop/TP
          oraz anulowanie (cancel) w każdej chwili.
        </p>
      </header>

      <PortfolioSummary portfolio={portfolio} />

      <section className="portfolio-section portfolio-actions-bar">
        <button type="button" className="btn-link tap-target" onClick={handleReset} disabled={resetting}>
          Reset konta
        </button>
      </section>

      <section className="portfolio-section">
        <div className="section-header">
          <div className="section-header-left">
            <h3 className="section-title">Otwarte zlecenia</h3>
            <span className="section-badge">{openOrders.length}</span>
          </div>
        </div>
        {openOrders.length === 0 ? (
          <p className="empty-state">Brak oczekujących zleceń. Ułóż limit, stop lub take profit przy pozycji.</p>
        ) : (
          <OpenOrdersPanel
            orders={openOrders}
            onCancel={handleCancelOrder}
            onCancelAll={handleCancelAll}
            cancellingId={cancellingId}
            cancellingAll={cancellingAll}
          />
        )}
      </section>

      <PositionsSection
        tab={positionsTab}
        onTabChange={setPositionsTab}
        openCount={portfolio.positions_count}
        closedCount={portfolio.closed_positions_count ?? closedPositions.length}
        positions={portfolio.positions}
        closedPositions={closedPositions}
        openOrders={openOrders}
        tradingSymbol={tradingSymbol}
        onTradeComplete={handleTradeComplete}
      />

      <section className="portfolio-section">
        <div className="section-header">
          <div className="section-header-left">
            <h3 className="section-title">Historia transakcji</h3>
            <span className="section-badge">{portfolio.recent_trades.length}</span>
          </div>
        </div>
        {portfolio.recent_trades.length === 0 ? (
          <p className="empty-state">Brak transakcji.</p>
        ) : (
          <div className="data-table trades-table">
            <div className="data-table-head">
              <span>Strona</span>
              <span>Symbol</span>
              <span>Ilość</span>
              <span>Kwota</span>
              <span>Czas</span>
            </div>
            {portfolio.recent_trades.map((t) => (
              <div key={t.id} className="data-table-row trade-row">
                <span className={`side-${t.side}`}>{t.side === 'buy' ? 'KUP' : 'SPRZEDAJ'}</span>
                <span className="trade-symbol">{t.symbol}</span>
                <span className="tabular">{t.quantity}</span>
                <span className="tabular">{formatPln(t.total_pln)}</span>
                <span className="trade-time">{new Date(t.created_at).toLocaleString('pl-PL')}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
