import { useLocale } from '../context/LocaleContext'
import { PaperLimitOrder } from '../types'
import { formatPln } from '../utils/format'

interface OpenOrdersPanelProps {
  orders: PaperLimitOrder[]
  onCancel?: (orderId: number) => void
  onCancelAll?: () => void
  cancellingId?: number | null
  cancellingAll?: boolean
  compact?: boolean
  title?: string
}

export function OpenOrdersPanel({
  orders,
  onCancel,
  onCancelAll,
  cancellingId,
  cancellingAll,
  compact,
  title,
}: OpenOrdersPanelProps) {
  const { t, dateLocale } = useLocale()

  const panelTitle = title ?? t('orders.title')

  const orderTypeLabel = (orderType: string) => {
    if (orderType === 'limit') return t('orders.limit')
    if (orderType === 'stop') return t('orders.stopLoss')
    if (orderType === 'take_profit') return t('orders.takeProfit')
    return orderType
  }

  const sideLabel = (side: string, orderType: string) => {
    if (orderType === 'stop') return side === 'sell' ? t('orders.slSell') : t('orders.slBuy')
    if (orderType === 'take_profit') return side === 'sell' ? t('orders.tpSell') : t('orders.tpBuy')
    return side === 'buy' ? t('orders.limitBuy') : t('orders.limitSell')
  }

  if (orders.length === 0) return null

  return (
    <div className={`open-orders-panel ${compact ? 'open-orders-panel-compact' : ''}`}>
      <div className="open-orders-head">
        <span className="open-orders-title">{panelTitle}</span>
        {onCancelAll && orders.length > 1 && (
          <button
            type="button"
            className="btn-link open-orders-cancel-all tap-target"
            disabled={cancellingAll}
            onClick={onCancelAll}
          >
            {cancellingAll ? '…' : t('orders.cancelAll')}
          </button>
        )}
      </div>

      {compact ? (
        <div className="pending-limit-orders pending-limit-orders-compact">
          {orders.map((o) => (
            <div key={o.id} className={`pending-limit-item side-${o.side} type-${o.order_type}`}>
              <div className="pending-limit-item-main">
                <span className="pending-limit-side">{sideLabel(o.side, o.order_type)}</span>
                <span className="pending-limit-type">{orderTypeLabel(o.order_type)}</span>
                <span className="pending-limit-price tabular">
                  @ {o.limit_price_native.toLocaleString(dateLocale)} {o.currency}
                </span>
                <span className="pending-limit-value tabular">
                  {formatPln(o.amount_pln)} · {t('orders.approxQty', { n: o.quantity_est })}
                </span>
              </div>
              {onCancel && (
                <button
                  type="button"
                  className="btn-cancel-order tap-target"
                  disabled={cancellingId === o.id}
                  onClick={() => onCancel(o.id)}
                >
                  {cancellingId === o.id ? '…' : t('orders.cancel')}
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="data-table open-orders-table">
          <div className="data-table-head">
            <span>{t('table.type')}</span>
            <span>{t('table.side')}</span>
            <span>{t('table.symbol')}</span>
            <span>{t('table.triggerPrice')}</span>
            <span>{t('table.value')}</span>
            <span aria-hidden />
          </div>
          {orders.map((o) => (
            <div key={o.id} className={`data-table-row open-order-row side-${o.side}`}>
              <span className="open-order-type">{orderTypeLabel(o.order_type)}</span>
              <span className={`side-${o.side}`}>
                {o.side === 'buy' ? t('portfolio.buySide') : t('portfolio.sellSide')}
              </span>
              <span className="trade-symbol">{o.symbol}</span>
              <span className="tabular">
                {o.limit_price_native.toLocaleString(dateLocale)} {o.currency}
                <em>
                  {formatPln(o.limit_price_pln)}
                  {t('table.perUnit')}
                </em>
              </span>
              <span className="tabular">
                {formatPln(o.amount_pln)}
                <em>{t('orders.approxQty', { n: o.quantity_est })}</em>
              </span>
              {onCancel && (
                <button
                  type="button"
                  className="btn-cancel-order tap-target"
                  disabled={cancellingId === o.id}
                  onClick={() => onCancel(o.id)}
                >
                  {cancellingId === o.id ? '…' : t('orders.cancel')}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** @deprecated */
export { OpenOrdersPanel as PendingLimitOrders }
