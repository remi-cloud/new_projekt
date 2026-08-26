import { useEffect, useMemo, useState } from 'react'
import { cancelPaperOrder, closePaperPosition, placePaperOrder } from '../api'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import { OpenOrdersPanel } from './OpenOrdersPanel'
import { PaperLimitOrder } from '../types'

type OrderType = 'market' | 'limit' | 'stop' | 'take_profit'

const CLOSE_PCTS = [25, 50, 75, 100] as const

function defaultTriggerPrice(type: OrderType, side: 'buy' | 'sell', live: number): number {
  if (type === 'market') return live
  if (type === 'limit') return side === 'buy' ? live * 0.97 : live * 1.03
  if (type === 'stop') return side === 'sell' ? live * 0.95 : live * 1.05
  return side === 'sell' ? live * 1.08 : live * 0.92
}

interface PositionTradeControlProps {
  symbol: string
  quantity: number
  isShort?: boolean
  priceNative: number
  pricePln: number
  currency: string
  pendingOrders?: PaperLimitOrder[]
  disabled?: boolean
  compact?: boolean
  onComplete: () => Promise<void>
  onClosed?: () => void
}

export function PositionTradeControl({
  symbol,
  quantity,
  isShort,
  priceNative,
  pricePln,
  currency,
  pendingOrders = [],
  disabled,
  compact,
  onComplete,
  onClosed,
}: PositionTradeControlProps) {
  const { t, dateLocale } = useLocale()
  const [orderType, setOrderType] = useState<OrderType>('stop')
  const [price, setPrice] = useState(String(priceNative))
  const [orderValue, setOrderValue] = useState('10000')
  const [busy, setBusy] = useState(false)
  const [closingPct, setClosingPct] = useState<number | null>(null)
  const [cancellingId, setCancellingId] = useState<number | null>(null)

  const formatQty = (qty: number): string => {
    if (qty >= 1) return qty.toLocaleString(dateLocale, { maximumFractionDigits: 4 })
    return qty.toPrecision(4)
  }

  useEffect(() => {
    const side = isShort ? 'buy' : 'sell'
    setPrice(String(defaultTriggerPrice(orderType, side, priceNative).toFixed(4)))
  }, [priceNative, symbol, orderType, isShort])

  const absQty = Math.abs(quantity)
  const priceNum = parseFloat(price) || 0
  const valueNum = parseFloat(orderValue) || 0
  const plnPerNative = priceNative > 0 ? pricePln / priceNative : 0
  const execPriceNative = orderType === 'market' ? priceNative : priceNum
  const estPricePln = execPriceNative * plnPerNative

  const estQty = useMemo(() => {
    if (estPricePln <= 0 || valueNum <= 0) return 0
    return valueNum / (estPricePln * 1.001)
  }, [estPricePln, valueNum])

  const confirmTypeLabel = (kind: OrderType) => {
    if (kind === 'market') return t('paper.market').toUpperCase()
    if (kind === 'limit') return t('orders.limit')
    if (kind === 'stop') return t('orders.stopLoss')
    return t('orders.takeProfit')
  }

  const handleCancel = async (orderId: number) => {
    if (!confirm(t('paper.confirmCancel'))) return
    setCancellingId(orderId)
    try {
      await cancelPaperOrder(orderId)
      await onComplete()
    } catch (e) {
      alert(formatThrownError(e, t('positions.cancelFailed')))
    } finally {
      setCancellingId(null)
    }
  }

  const handleClosePct = async (percent: number) => {
    // No window.confirm — Simple Browser / embedded previews often block dialogs
    // and make close look "broken". One-click market close like pro desks.
    setClosingPct(percent)
    setBusy(true)
    try {
      await closePaperPosition(symbol, percent)
      await onComplete()
      onClosed?.()
    } catch (e) {
      alert(formatThrownError(e, t('api.closePosition')))
    } finally {
      setBusy(false)
      setClosingPct(null)
    }
  }

  const submit = async (side: 'buy' | 'sell') => {
    if (valueNum <= 0) {
      alert(t('positions.enterValue'))
      return
    }
    if (orderType !== 'market' && priceNum <= 0) {
      alert(t('paper.enterTrigger'))
      return
    }

    const trigger = orderType === 'market' ? priceNative : priceNum

    if (
      !confirm(
        t('paper.confirmSummary', {
          type: confirmTypeLabel(orderType),
          action: side === 'buy' ? t('paper.actionBuy') : t('paper.actionSell'),
          symbol,
          position: isShort ? t('paper.positionShort') : t('paper.positionLong'),
          trigger,
          currency,
          value: valueNum.toLocaleString(dateLocale),
          qty: formatQty(estQty),
        }),
      )
    ) {
      return
    }

    setBusy(true)
    try {
      const res = await placePaperOrder({
        symbol,
        side,
        amount_pln: valueNum,
        order_type: orderType,
        limit_price_native: orderType === 'market' ? undefined : trigger,
      })
      const status = (res as { status?: string }).status
      if (status === 'pending') {
        alert(t('paper.orderPending'))
      }
      await onComplete()
    } catch (e) {
      alert(formatThrownError(e, t('paper.tradeFailed')))
    } finally {
      setBusy(false)
    }
  }

  const isDisabled = disabled || busy
  const reduceSide: 'buy' | 'sell' = isShort ? 'buy' : 'sell'

  const tabLabel = (kind: OrderType) => {
    if (kind === 'market') return t('paper.market')
    if (kind === 'limit') return t('paper.limit')
    if (kind === 'stop') return t('paper.stop')
    return t('paper.tp')
  }

  return (
    <div className={`position-trade-control ${compact ? 'position-trade-control-compact' : ''}`}>
      <div className="position-close-strip">
        <div className="position-close-strip-head">
          <span className="position-close-label">
            {isShort ? t('positions.closeCover') : t('positions.closeLabel')}
          </span>
          <span className="position-close-hint">{t('positions.closeHint')}</span>
        </div>
        <div className="position-close-pcts" role="group" aria-label={t('positions.closeLabel')}>
          {CLOSE_PCTS.map((pct) => (
            <button
              key={pct}
              type="button"
              className={`btn-close-position ${pct === 100 ? 'btn-close-position-prominent' : ''}`}
              disabled={isDisabled}
              onClick={() => void handleClosePct(pct)}
            >
              {closingPct === pct ? '…' : pct === 100 ? t('positions.closeAll') : `${pct}%`}
            </button>
          ))}
        </div>
      </div>

      <OpenOrdersPanel
        orders={pendingOrders}
        compact
        onCancel={handleCancel}
        cancellingId={cancellingId}
      />

      <div className="position-trade-header">
        <span className="position-trade-label">{t('positions.autoProtect')}</span>
        <span className="position-trade-qty tabular">
          {isShort ? `${t('common.short')} ` : ''}
          {formatQty(absQty)} {t('paper.pieces')}
        </span>
      </div>

      <div className="trade-mode-tabs position-trade-type-tabs">
        {(['market', 'limit', 'stop', 'take_profit'] as OrderType[]).map((kind) => (
          <button
            key={kind}
            type="button"
            className={orderType === kind ? 'active' : ''}
            disabled={isDisabled}
            onClick={() => setOrderType(kind)}
          >
            {tabLabel(kind)}
          </button>
        ))}
      </div>

      {orderType === 'market' ? (
        <p className="position-trade-live-price tabular">
          {t('paper.marketPrice', {
            price: priceNative.toLocaleString(dateLocale),
            currency,
          })}
        </p>
      ) : (
        <label className="position-trade-field">
          <span>
            {t('paper.triggerPrice')} ({currency})
            {orderType === 'limit' && ` · ${t('paper.limit').toLowerCase()}`}
            {orderType === 'stop' && ` · ${t('orders.stopLoss').toLowerCase()}`}
            {orderType === 'take_profit' && ` · ${t('orders.takeProfit').toLowerCase()}`}
          </span>
          <input
            className="field-input"
            type="number"
            min={0}
            step="any"
            value={price}
            disabled={isDisabled}
            onChange={(e) => setPrice(e.target.value)}
          />
        </label>
      )}

      <label className="position-trade-field">
        <span>{t('paper.orderValue')}</span>
        <input
          className="field-input"
          type="number"
          min={100}
          step={1000}
          value={orderValue}
          disabled={isDisabled}
          onChange={(e) => setOrderValue(e.target.value)}
        />
      </label>

      {valueNum > 0 && estQty > 0 && (
        <p className="position-trade-estimate tabular">{t('paper.estimate', { n: formatQty(estQty) })}</p>
      )}

      <div className="position-trade-actions">
        <button type="button" className="btn-buy tap-target" disabled={isDisabled} onClick={() => submit('buy')}>
          {t('positions.addTo')}
        </button>
        <button
          type="button"
          className="btn-sell tap-target"
          disabled={isDisabled}
          onClick={() => submit(reduceSide)}
        >
          {isShort ? t('positions.coverBtn') : t('positions.sellBtn')}
        </button>
      </div>
    </div>
  )
}

export { PositionTradeControl as ClosePositionControl }
