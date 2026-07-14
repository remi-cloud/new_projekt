import { PaperLimitOrder } from '../types'
import { formatPln } from '../utils/format'

const ORDER_TYPE_LABEL: Record<string, string> = {
  limit: 'LIMIT',
  stop: 'STOP LOSS',
  take_profit: 'TAKE PROFIT',
}

function sideLabel(side: string, orderType: string): string {
  if (orderType === 'stop') return side === 'sell' ? 'SL · SPRZEDAJ' : 'SL · KUP'
  if (orderType === 'take_profit') return side === 'sell' ? 'TP · SPRZEDAJ' : 'TP · KUP'
  return side === 'buy' ? 'LIMIT · KUP' : 'LIMIT · SPRZEDAJ'
}

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
  title = 'Otwarte zlecenia',
}: OpenOrdersPanelProps) {
  if (orders.length === 0) return null

  return (
    <div className={`open-orders-panel ${compact ? 'open-orders-panel-compact' : ''}`}>
      <div className="open-orders-head">
        <span className="open-orders-title">{title}</span>
        {onCancelAll && orders.length > 1 && (
          <button
            type="button"
            className="btn-link open-orders-cancel-all tap-target"
            disabled={cancellingAll}
            onClick={onCancelAll}
          >
            {cancellingAll ? '…' : 'Anuluj wszystkie'}
          </button>
        )}
      </div>

      {compact ? (
        <div className="pending-limit-orders pending-limit-orders-compact">
          {orders.map((o) => (
            <div key={o.id} className={`pending-limit-item side-${o.side} type-${o.order_type}`}>
              <div className="pending-limit-item-main">
                <span className="pending-limit-side">{sideLabel(o.side, o.order_type)}</span>
                <span className="pending-limit-type">{ORDER_TYPE_LABEL[o.order_type] ?? o.order_type}</span>
                <span className="pending-limit-price tabular">
                  @ {o.limit_price_native.toLocaleString('pl-PL')} {o.currency}
                </span>
                <span className="pending-limit-value tabular">
                  {formatPln(o.amount_pln)} · ≈ {o.quantity_est} szt.
                </span>
              </div>
              {onCancel && (
                <button
                  type="button"
                  className="btn-cancel-order tap-target"
                  disabled={cancellingId === o.id}
                  onClick={() => onCancel(o.id)}
                >
                  {cancellingId === o.id ? '…' : 'Cancel'}
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="data-table open-orders-table">
          <div className="data-table-head">
            <span>Typ</span>
            <span>Strona</span>
            <span>Symbol</span>
            <span>Cena trigger</span>
            <span>Wartość</span>
            <span aria-hidden />
          </div>
          {orders.map((o) => (
            <div key={o.id} className={`data-table-row open-order-row side-${o.side}`}>
              <span className="open-order-type">{ORDER_TYPE_LABEL[o.order_type] ?? o.order_type}</span>
              <span className={`side-${o.side}`}>{o.side === 'buy' ? 'KUP' : 'SPRZEDAJ'}</span>
              <span className="trade-symbol">{o.symbol}</span>
              <span className="tabular">
                {o.limit_price_native.toLocaleString('pl-PL')} {o.currency}
                <em>{formatPln(o.limit_price_pln)}/szt.</em>
              </span>
              <span className="tabular">
                {formatPln(o.amount_pln)}
                <em>≈ {o.quantity_est} szt.</em>
              </span>
              {onCancel && (
                <button
                  type="button"
                  className="btn-cancel-order tap-target"
                  disabled={cancellingId === o.id}
                  onClick={() => onCancel(o.id)}
                >
                  {cancellingId === o.id ? '…' : 'Cancel'}
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
