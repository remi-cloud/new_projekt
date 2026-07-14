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
import { PaperPortfolio as PaperPortfolioType, PaperPosition } from '../types'
import { formatPln } from '../utils/format'

export { usePaperPortfolio } from '../context/DashboardContext'

function formatOpenedAt(iso?: string): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString('pl-PL')
}

interface TradePanelProps {
  symbol: string
  name: string
  price: number
  onTrade?: () => void
}

export function TradePanel({ symbol, name, price, onTrade }: TradePanelProps) {
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
        setMsg('Podaj cenę trigger')
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
        setMsg('Zlecenie złożone — oczekuje na trigger ✓')
      } else {
        setMsg(side === 'buy' ? 'Kupiono ✓' : 'Sprzedano ✓')
      }
      reloadPosition()
      reloadPortfolio()
      onTrade?.()
    } catch (e) {
      const err = e as Error
      setMsg(err.message || 'Transakcja nieudana')
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
    if (!confirm('Anulować zlecenie?')) return
    setCancellingId(orderId)
    try {
      await cancelPaperOrder(orderId)
      reloadPosition()
      reloadPortfolio()
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setCancellingId(null)
    }
  }

  return (
    <div className="trade-panel terminal-trade-panel" onClick={(e) => e.stopPropagation()}>
      <div className="trade-panel-head">
        <span className="trade-panel-eyebrow">Order Entry · Paper</span>
        <h4>{name}</h4>
      </div>
      <p className="trade-price-hint">
        Cena live <span className="tabular">{price}</span>
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
              {position.is_short ? 'SHORT' : 'LONG'}
            </span>
            <span>{Math.abs(position.quantity)} szt.</span>
            <span className={position.unrealized_pnl_pln >= 0 ? 'positive' : 'negative'}>
              {position.unrealized_pnl_pln >= 0 ? '+' : ''}
              {formatPln(position.unrealized_pnl_pln)} ({position.unrealized_pnl_pct}%)
            </span>
          </div>
          {formatOpenedAt(position.opened_at) && (
            <p className="position-opened-at">Otwarto: {formatOpenedAt(position.opened_at)}</p>
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
        {(['market', 'limit', 'stop', 'take_profit'] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={orderType === t ? 'active' : ''}
            onClick={() => setOrderType(t)}
          >
            {t === 'market' ? 'Rynek' : t === 'limit' ? 'Limit' : t === 'stop' ? 'Stop' : 'TP'}
          </button>
        ))}
      </div>

      {orderType !== 'market' && (
        <label className="field-label">
          Cena trigger
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
          Kwota PLN
        </button>
        <button type="button" className={mode === 'qty' ? 'active' : ''} onClick={() => setMode('qty')}>
          Ilość
        </button>
      </div>

      {mode === 'pln' ? (
        <label className="field-label">
          Kwota (PLN)
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
          Ilość {maxQty != null && `(max: ${maxQty})`}
          <input
            className="field-input"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            min={0}
            step="any"
            placeholder="np. 10"
          />
        </label>
      )}

      <div className="trade-actions">
        <button type="button" className="btn-buy tap-target" disabled={busy} onClick={() => submit('buy')}>
          Kupuj
        </button>
        <button type="button" className="btn-sell tap-target" disabled={busy} onClick={() => submit('sell')}>
          Sprzedaj
        </button>
      </div>
      {maxQty != null && mode === 'qty' && (
        <button
          type="button"
          className="btn-link tap-target"
          onClick={() => setQuantity(String(maxQty))}
        >
          Max ({maxQty})
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
  const pnlClass = portfolio.total_pnl_pln >= 0 ? 'positive' : 'negative'
  return (
    <div className="portfolio-summary portfolio-summary-hero">
      <div className="portfolio-hero">
        <div className="stat-label">Net Asset Value</div>
        <div className="portfolio-equity tabular">{formatPln(portfolio.total_equity_pln)}</div>
        <div className={`portfolio-pnl ${pnlClass}`}>
          {portfolio.total_pnl_pln >= 0 ? '+' : ''}
          {formatPln(portfolio.total_pnl_pln)} ({portfolio.total_pnl_pct}%)
        </div>
      </div>
      <div className="portfolio-stats-row">
        <div className="mini-stat">
          <span>Cash</span>
          <strong className="tabular">{formatPln(portfolio.cash_pln)}</strong>
        </div>
        <div className="mini-stat">
          <span>Positions</span>
          <strong className="tabular">{formatPln(portfolio.positions_value_pln)}</strong>
        </div>
        <div className="mini-stat">
          <span>USD/PLN</span>
          <strong className="tabular">{portfolio.usd_pln_rate.toFixed(4)}</strong>
        </div>
      </div>
    </div>
  )
}
