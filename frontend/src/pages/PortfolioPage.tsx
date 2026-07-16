import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { PortfolioSummary, usePaperPortfolio } from '../components/PaperTrading'
import { OpenOrdersPanel } from '../components/OpenOrdersPanel'
import { PositionsSection } from '../components/PositionsSection'
import { ErrorState } from '../components/Loading'
import { resetPaperPortfolio, cancelPaperOrder, cancelAllPaperOrders } from '../api'
import { formatPln } from '../utils/format'
import { useLocale } from '../context/LocaleContext'

export function PortfolioPage() {
  const location = useLocation()
  const { t, dateLocale } = useLocale()
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
    if (!confirm(t('portfolio.confirmCancel'))) return
    setCancellingId(orderId)
    try {
      await cancelPaperOrder(orderId)
      await reload()
    } catch (e) {
      alert((e as Error).message || t('api.cancelOrder'))
    } finally {
      setCancellingId(null)
    }
  }

  const handleCancelAll = async () => {
    if (!confirm(t('portfolio.confirmCancelAll'))) return
    setCancellingAll(true)
    try {
      await cancelAllPaperOrders()
      await reload()
    } catch (e) {
      alert((e as Error).message || t('api.cancelOrder'))
    } finally {
      setCancellingAll(false)
    }
  }

  const handleReset = async () => {
    if (!confirm(t('portfolio.confirmReset'))) return
    setResetting(true)
    try {
      await resetPaperPortfolio()
      await reload()
    } finally {
      setResetting(false)
    }
  }

  if (loading && !portfolio) return <div className="page-loading">{t('portfolio.loading')}</div>
  if (error && !portfolio) return <ErrorState message={error} onRetry={reload} />
  if (!portfolio) return null

  const openOrders = portfolio.limit_orders ?? []
  const closedPositions = portfolio.closed_positions ?? []

  return (
    <div className="portfolio-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('portfolio.eyebrow')}</span>
        <h2 className="page-headline">{t('portfolio.title')}</h2>
        <p className="page-lead">{t('portfolio.lead')}</p>
      </header>

      <PortfolioSummary portfolio={portfolio} />

      <section className="portfolio-section portfolio-actions-bar">
        <button type="button" className="btn-link tap-target" onClick={handleReset} disabled={resetting}>
          {t('portfolio.resetAccount')}
        </button>
      </section>

      <section className="portfolio-section">
        <div className="section-header">
          <div className="section-header-left">
            <h3 className="section-title">{t('portfolio.openOrders')}</h3>
            <span className="section-badge">{openOrders.length}</span>
          </div>
        </div>
        {openOrders.length === 0 ? (
          <p className="empty-state">{t('portfolio.emptyOrders')}</p>
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
            <h3 className="section-title">{t('portfolio.tradeHistory')}</h3>
            <span className="section-badge">{portfolio.recent_trades.length}</span>
          </div>
        </div>
        {portfolio.recent_trades.length === 0 ? (
          <p className="empty-state">{t('portfolio.emptyTrades')}</p>
        ) : (
          <div className="data-table trades-table">
            <div className="data-table-head">
              <span>{t('portfolio.tableSide')}</span>
              <span>{t('portfolio.tableSymbol')}</span>
              <span>{t('portfolio.tableQty')}</span>
              <span>{t('portfolio.tableAmount')}</span>
              <span>{t('portfolio.tableTime')}</span>
            </div>
            {portfolio.recent_trades.map((trade) => (
              <div key={trade.id} className="data-table-row trade-row">
                <span className={`side-${trade.side}`}>
                  {trade.side === 'buy' ? t('portfolio.buySide') : t('portfolio.sellSide')}
                </span>
                <span className="trade-symbol">{trade.symbol}</span>
                <span className="tabular">{trade.quantity}</span>
                <span className="tabular">{formatPln(trade.total_pln)}</span>
                <span className="trade-time">{new Date(trade.created_at).toLocaleString(dateLocale)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
