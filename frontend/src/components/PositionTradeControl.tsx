import { useEffect, useMemo, useState } from 'react'
import { cancelPaperOrder, placePaperOrder } from '../api'
import { OpenOrdersPanel } from './OpenOrdersPanel'
import { PaperLimitOrder } from '../types'

function formatQty(qty: number): string {
  if (qty >= 1) return qty.toLocaleString('pl-PL', { maximumFractionDigits: 4 })
  return qty.toPrecision(4)
}

type OrderType = 'market' | 'limit' | 'stop' | 'take_profit'

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
}: PositionTradeControlProps) {
  const [orderType, setOrderType] = useState<OrderType>('limit')
  const [price, setPrice] = useState(String(priceNative))
  const [orderValue, setOrderValue] = useState('10000')
  const [busy, setBusy] = useState(false)
  const [cancellingId, setCancellingId] = useState<number | null>(null)

  useEffect(() => {
    setPrice(String(defaultTriggerPrice(orderType, 'buy', priceNative).toFixed(4)))
  }, [priceNative, symbol, orderType])

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

  const handleCancel = async (orderId: number) => {
    if (!confirm('Anulować zlecenie?')) return
    setCancellingId(orderId)
    try {
      await cancelPaperOrder(orderId)
      await onComplete()
    } catch (e) {
      alert((e as Error).message || 'Nie udało się anulować')
    } finally {
      setCancellingId(null)
    }
  }

  const submit = async (side: 'buy' | 'sell') => {
    if (valueNum <= 0) {
      alert('Podaj wartość zamówienia w PLN')
      return
    }
    if (orderType !== 'market' && priceNum <= 0) {
      alert('Podaj cenę trigger')
      return
    }

    const trigger = orderType === 'market' ? priceNative : priceNum

    const action = side === 'buy' ? 'DOKUP' : 'SPRZEDAŻ'
    const typeLabel = orderType.toUpperCase().replace('_', ' ')
    const positionLabel = isShort ? 'short' : 'long'

    if (
      !confirm(
        `${typeLabel} · ${action} · ${symbol} (${positionLabel})\nTrigger: ${trigger} ${currency}\nWartość: ${valueNum.toLocaleString('pl-PL')} PLN\n~${formatQty(estQty)} szt.`,
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
        alert('Zlecenie złożone — oczekuje na trigger ✓')
      }
      await onComplete()
    } catch (e) {
      alert((e as Error).message || 'Transakcja nieudana')
    } finally {
      setBusy(false)
    }
  }

  const isDisabled = disabled || busy

  return (
    <div className={`position-trade-control ${compact ? 'position-trade-control-compact' : ''}`}>
      <OpenOrdersPanel
        orders={pendingOrders}
        compact
        title="Otwarte zlecenia"
        onCancel={handleCancel}
        cancellingId={cancellingId}
      />

      <div className="position-trade-header">
        <span className="position-trade-label">Zlecenie</span>
        <span className="position-trade-qty tabular">
          {isShort ? 'SHORT ' : ''}
          {formatQty(absQty)} szt.
        </span>
      </div>

      <div className="trade-mode-tabs position-trade-type-tabs">
        {(['market', 'limit', 'stop', 'take_profit'] as OrderType[]).map((t) => (
          <button
            key={t}
            type="button"
            className={orderType === t ? 'active' : ''}
            disabled={isDisabled}
            onClick={() => setOrderType(t)}
          >
            {t === 'market' ? 'Rynek' : t === 'limit' ? 'Limit' : t === 'stop' ? 'Stop' : 'TP'}
          </button>
        ))}
      </div>

      {orderType === 'market' ? (
        <p className="position-trade-live-price tabular">
          Cena rynkowa: {priceNative.toLocaleString('pl-PL')} {currency}
        </p>
      ) : (
        <label className="position-trade-field">
          <span>
            Cena trigger ({currency})
            {orderType === 'limit' && ' · limit'}
            {orderType === 'stop' && ' · stop loss'}
            {orderType === 'take_profit' && ' · take profit'}
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
        <span>Wartość zamówienia (PLN)</span>
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
        <p className="position-trade-estimate tabular">≈ {formatQty(estQty)} szt.</p>
      )}

      <div className="position-trade-actions">
        <button type="button" className="btn-buy tap-target" disabled={isDisabled} onClick={() => submit('buy')}>
          Dokup
        </button>
        <button type="button" className="btn-sell tap-target" disabled={isDisabled} onClick={() => submit('sell')}>
          Sprzedaj
        </button>
      </div>
    </div>
  )
}

export { PositionTradeControl as ClosePositionControl }
