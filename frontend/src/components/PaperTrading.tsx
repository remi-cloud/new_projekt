import { useCallback, useEffect, useState } from 'react'
import {
  fetchPaperMaxBuy,
  fetchPaperPortfolio,
  fetchPaperPosition,
  placePaperOrder,
  cancelPaperOrder,
} from '../api'
import { PositionTradeControl } from './PositionTradeControl'
import { OpenOrdersPanel } from './OpenOrdersPanel'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import { PaperPortfolio as PaperPortfolioType, PaperPosition } from '../types'
import { formatPln } from '../utils/format'

export { usePaperPortfolio } from '../context/DashboardContext'

interface TradePanelProps {
  symbol: string
  name: string
  price: number
  onTrade?: () => void
}

export function TradePanel({ symbol, name, price, onTrade }: TradePanelProps) {
  const { t, dateLocale } = useLocale()
  const { lastEventAt, reloadPortfolio, portfolio } = useDashboardContext()
  const [mode, setMode] = useState<'qty' | 'pln'>('pln')
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop' | 'take_profit'>('market')
  const [limitPrice, setLimitPrice] = useState(String(price))
  const [quantity, setQuantity] = useState('')
  const [amountPln, setAmountPln] = useState('50000')
  const [maxQty, setMaxQty] = useState<number | null>(null)
  const [position, setPosition] = useState<PaperPosition | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<number | null>(null)

  const formatOpenedAt = (iso?: string): string | null => {
    if (!iso) return null
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return null
    return d.toLocaleString(dateLocale)
  }

  const symbolOpenOrders = (portfolio?.limit_orders ?? []).filter((o) => o.symbol === symbol)

  const reloadPosition = useCallback(() => {
    fetchPaperPosition(symbol)
      .then(setPosition)
      .catch(() => {
        fetchPaperPortfolio()
          .then((pf) => setPosition(pf.positions.find((p) => p.symbol === symbol) ?? null))
          .catch(() => setPosition(null))
      })
  }, [symbol])

  useEffect(() => {
    fetchPaperMaxBuy(symbol).then((r) => setMaxQty(r.max_quantity)).catch(() => {})
    reloadPosition()
  }, [symbol, reloadPosition])

  useEffect(() => {
    if (lastEventAt) reloadPosition()
  }, [lastEventAt, reloadPosition])

  useEffect(() => {
    setLimitPrice(String(price))
  }, [price, symbol])

  const submit = async (side: 'buy' | 'sell') => {
    setBusy(true)
    setMsg(null)
    try {
      const limitNum = parseFloat(limitPrice)
      if (orderType !== 'market' && (!limitNum || limitNum <= 0)) {
        setMsg(t('paper.enterTrigger'))
        return
      }
      const body =
        mode === 'pln'
          ? {
              symbol,
              side,
              amount_pln: parseFloat(amountPln),
              order_type: orderType,
              limit_price_native: orderType === 'market' ? undefined : limitNum,
            }
          : {
              symbol,
              side,
              quantity: parseFloat(quantity),
              order_type: orderType,
              limit_price_native: orderType === 'market' ? undefined : limitNum,
            }
      const res = await placePaperOrder(body)
      const status = (res as { status?: string }).status
      if (status === 'pending') {
        setMsg(t('paper.orderPending'))
      } else {
        setMsg(side === 'buy' ? t('paper.bought') : t('paper.sold'))
      }
      reloadPosition()
      reloadPortfolio()
      onTrade?.()
    } catch (e) {
      setMsg(formatThrownError(e, t('paper.tradeFailed')))
    } finally {
      setBusy(false)
    }
  }

  const handlePositionTrade = async () => {
    reloadPosition()
    reloadPortfolio()
    onTrade?.()
  }

  const handleCancelOrder = async (orderId: number) => {
    if (!confirm(t('paper.confirmCancel'))) return
    setCancellingId(orderId)
    try {
      await cancelPaperOrder(orderId)
      reloadPosition()
      reloadPortfolio()
    } catch (e) {
      alert(formatThrownError(e, t('api.cancelOrder')))
    } finally {
      setCancellingId(null)
    }
  }

  const orderTypeLabel = (kind: typeof orderType) => {
    if (kind === 'market') return t('paper.market')
    if (kind === 'limit') return t('paper.limit')
    if (kind === 'stop') return t('paper.stop')
    return t('paper.tp')
  }

  return (
    <div className="trade-panel terminal-trade-panel" onClick={(e) => e.stopPropagation()}>
      <div className="trade-panel-head">
        <span className="trade-panel-eyebrow">{t('paper.orderEntry')}</span>
        <h4>{name}</h4>
      </div>
      <p className="trade-price-hint">
        {t('paper.livePrice')} <span className="tabular">{price}</span>
      </p>

      <OpenOrdersPanel
        orders={symbolOpenOrders}
        compact
        onCancel={handleCancelOrder}
        cancellingId={cancellingId}
      />

      {position && (
        <div className="position-open">
          <div className="position-open-main">
            <span className={position.is_short ? 'side-sell' : 'side-buy'}>
              {position.is_short ? t('common.short') : t('common.long')}
            </span>
            <span>
              {Math.abs(position.quantity)} {t('paper.pieces')}
            </span>
            <span className={position.unrealized_pnl_pln >= 0 ? 'positive' : 'negative'}>
              {position.unrealized_pnl_pln >= 0 ? '+' : ''}
              {formatPln(position.unrealized_pnl_pln)} ({position.unrealized_pnl_pct}%)
            </span>
          </div>
          {formatOpenedAt(position.opened_at) && (
            <p className="position-opened-at">
              {t('paper.openedAt')} {formatOpenedAt(position.opened_at)}
            </p>
          )}
          <PositionTradeControl
            symbol={symbol}
            quantity={position.quantity}
            isShort={position.is_short}
            priceNative={position.current_price_native}
            pricePln={position.current_price_pln}
            currency={position.currency}
            pendingOrders={position.pending_limit_orders ?? symbolOpenOrders}
            disabled={busy}
            onComplete={handlePositionTrade}
          />
        </div>
      )}

      <div className="trade-mode-tabs">
        {(['market', 'limit', 'stop', 'take_profit'] as const).map((kind) => (
          <button
            key={kind}
            type="button"
            className={orderType === kind ? 'active' : ''}
            onClick={() => setOrderType(kind)}
          >
            {orderTypeLabel(kind)}
          </button>
        ))}
      </div>

      {orderType !== 'market' && (
        <label className="field-label">
          {t('paper.triggerPrice')}
          <input
            className="field-input"
            type="number"
            value={limitPrice}
            onChange={(e) => setLimitPrice(e.target.value)}
            min={0}
            step="any"
          />
        </label>
      )}

      <div className="trade-mode-tabs">
        <button type="button" className={mode === 'pln' ? 'active' : ''} onClick={() => setMode('pln')}>
          {t('paper.amountPln')}
        </button>
        <button type="button" className={mode === 'qty' ? 'active' : ''} onClick={() => setMode('qty')}>
          {t('paper.quantity')}
        </button>
      </div>

      {mode === 'pln' ? (
        <label className="field-label">
          {t('paper.amountLabel')}
          <input
            className="field-input"
            type="number"
            value={amountPln}
            onChange={(e) => setAmountPln(e.target.value)}
            min={1000}
            step={1000}
          />
        </label>
      ) : (
        <label className="field-label">
          {t('paper.quantity')} {maxQty != null && `(${t('paper.max', { n: maxQty })})`}
          <input
            className="field-input"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            min={0}
            step="any"
            placeholder={t('paper.qtyPlaceholder')}
          />
        </label>
      )}

      <div className="trade-actions">
        <button type="button" className="btn-buy tap-target" disabled={busy} onClick={() => submit('buy')}>
          {t('paper.buy')}
        </button>
        <button type="button" className="btn-sell tap-target" disabled={busy} onClick={() => submit('sell')}>
          {t('paper.sell')}
        </button>
      </div>
      {maxQty != null && mode === 'qty' && (
        <button
          type="button"
          className="btn-link tap-target"
          onClick={() => setQuantity(String(maxQty))}
        >
          {t('paper.max', { n: maxQty })}
        </button>
      )}
      {mode === 'pln' && (
        <div className="quick-amounts">
          {[10000, 50000, 100000, 250000].map((a) => (
            <button key={a} type="button" className="quick-amt" onClick={() => setAmountPln(String(a))}>
              {a / 1000}k
            </button>
          ))}
        </div>
      )}
      {msg && <p className="trade-msg">{msg}</p>}
    </div>
  )
}

export function PortfolioSummary({ portfolio }: { portfolio: PaperPortfolioType }) {
  const { t } = useLocale()
  const pnlClass = portfolio.total_pnl_pln >= 0 ? 'positive' : 'negative'
  const unrealizedClass = portfolio.unrealized_pnl_pln >= 0 ? 'positive' : 'negative'
  const realizedClass = portfolio.realized_pnl_pln >= 0 ? 'positive' : 'negative'
  const stats = portfolio.trade_stats
  return (
    <div className="portfolio-summary portfolio-summary-hero">
      <div className="portfolio-hero">
        <div className="stat-label">{t('paper.nav')}</div>
        <div className="portfolio-equity tabular">{formatPln(portfolio.total_equity_pln)}</div>
        <div className={`portfolio-pnl ${pnlClass}`}>
          {portfolio.total_pnl_pln >= 0 ? '+' : ''}
          {formatPln(portfolio.total_pnl_pln)} ({portfolio.total_pnl_pct}%)
        </div>
      </div>
      <div className="portfolio-stats-row">
        <div className="mini-stat">
          <span>{t('paper.cash')}</span>
          <strong className="tabular">{formatPln(portfolio.cash_pln)}</strong>
        </div>
        <div className="mini-stat">
          <span>{t('paper.positions')}</span>
          <strong className="tabular">{formatPln(portfolio.positions_value_pln)}</strong>
        </div>
        <div className="mini-stat">
          <span>{t('paper.usdPln')}</span>
          <strong className="tabular">{portfolio.usd_pln_rate.toFixed(4)}</strong>
        </div>
      </div>
      <div className="portfolio-stats-row portfolio-pnl-breakdown">
        <div className="mini-stat">
          <span>{t('portfolio.unrealizedPnl')}</span>
          <strong className={`tabular ${unrealizedClass}`}>
            {portfolio.unrealized_pnl_pln >= 0 ? '+' : ''}
            {formatPln(portfolio.unrealized_pnl_pln)}
          </strong>
        </div>
        <div className="mini-stat">
          <span>{t('portfolio.realizedPnl')}</span>
          <strong className={`tabular ${realizedClass}`}>
            {portfolio.realized_pnl_pln >= 0 ? '+' : ''}
            {formatPln(portfolio.realized_pnl_pln)}
          </strong>
        </div>
        <div className="mini-stat">
          <span>{t('portfolio.totalPnl')}</span>
          <strong className={`tabular ${pnlClass}`}>
            {portfolio.total_pnl_pln >= 0 ? '+' : ''}
            {formatPln(portfolio.total_pnl_pln)}
          </strong>
        </div>
      </div>
      {stats && stats.trades > 0 ? (
        <div className="portfolio-stats-row portfolio-trade-stats" aria-label={t('portfolio.tradeStats')}>
          <div className="mini-stat">
            <span>{t('portfolio.winRate')}</span>
            <strong className="tabular">
              {stats.win_rate != null ? `${stats.win_rate}%` : '—'}
            </strong>
          </div>
          <div className="mini-stat">
            <span>{t('portfolio.tradeCount')}</span>
            <strong className="tabular">{stats.trades}</strong>
          </div>
          <div className="mini-stat">
            <span>{t('portfolio.expectancy')}</span>
            <strong className="tabular">
              {stats.expectancy_pln != null
                ? `${stats.expectancy_pln >= 0 ? '+' : ''}${formatPln(stats.expectancy_pln)}`
                : '—'}
            </strong>
          </div>
        </div>
      ) : null}
    </div>
  )
}
