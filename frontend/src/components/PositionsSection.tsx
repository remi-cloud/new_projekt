import { Link } from 'react-router-dom'
import { PaperClosedPosition, PaperLimitOrder, PaperPosition } from '../types'
import { formatPln } from '../utils/format'
import { PositionTradeControl } from './PositionTradeControl'

function formatDt(iso?: string): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString('pl-PL')
}

interface PositionsSectionProps {
  tab: 'open' | 'closed'
  onTabChange: (tab: 'open' | 'closed') => void
  openCount: number
  closedCount: number
  positions: PaperPosition[]
  closedPositions: PaperClosedPosition[]
  openOrders: PaperLimitOrder[]
  tradingSymbol: string | null
  onTradeComplete: (symbol: string) => Promise<void>
}

export function PositionsSection({
  tab,
  onTabChange,
  openCount,
  closedCount,
  positions,
  closedPositions,
  openOrders,
  tradingSymbol,
  onTradeComplete,
}: PositionsSectionProps) {
  return (
    <section className="portfolio-section positions-section">
      <div className="section-header">
        <div className="section-header-left">
          <h3 className="section-title">Pozycje</h3>
          <div className="position-tabs" role="tablist" aria-label="Otwarte i zamknięte pozycje">
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'open'}
              className={`position-tab ${tab === 'open' ? 'active' : ''}`}
              onClick={() => onTabChange('open')}
            >
              Otwarte
              <span className="position-tab-count">{openCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'closed'}
              className={`position-tab ${tab === 'closed' ? 'active' : ''}`}
              onClick={() => onTabChange('closed')}
            >
              Zamknięte
              <span className="position-tab-count">{closedCount}</span>
            </button>
          </div>
        </div>
      </div>

      {tab === 'open' ? (
        openCount === 0 ? (
          <p className="empty-state">Brak otwartych pozycji. Kup instrument na stronie Rynki.</p>
        ) : (
          <div className="data-table positions-table">
            <div className="data-table-head">
              <span>Instrument</span>
              <span>Ilość</span>
              <span>Wartość</span>
              <span>P/L (nereal.)</span>
              <span aria-hidden />
            </div>
            {positions.map((p) => (
              <div key={p.symbol} className="data-table-row position-row">
                <Link
                  to={`/instrument/${encodeURIComponent(p.symbol)}`}
                  className="position-row-link tap-target"
                >
                  <div className="position-main">
                    <strong className="position-symbol">{p.symbol}</strong>
                    <span className="position-name">{p.name}</span>
                    {formatDt(p.opened_at) && (
                      <span className="position-opened-at">Otwarto {formatDt(p.opened_at)}</span>
                    )}
                  </div>
                  <span className="position-qty tabular">
                    {p.is_short ? `SHORT ${Math.abs(p.quantity)}` : p.quantity}
                  </span>
                  <span className="position-value tabular">{formatPln(p.market_value_pln)}</span>
                  <span
                    className={`position-pnl tabular ${p.unrealized_pnl_pln >= 0 ? 'positive' : 'negative'}`}
                  >
                    {p.unrealized_pnl_pln >= 0 ? '+' : ''}
                    {formatPln(p.unrealized_pnl_pln)}
                    <em>{p.unrealized_pnl_pct}%</em>
                  </span>
                </Link>
                <PositionTradeControl
                  symbol={p.symbol}
                  quantity={p.quantity}
                  isShort={p.is_short}
                  priceNative={p.current_price_native}
                  pricePln={p.current_price_pln}
                  currency={p.currency}
                  pendingOrders={p.pending_limit_orders ?? openOrders.filter((o) => o.symbol === p.symbol)}
                  compact
                  disabled={tradingSymbol === p.symbol}
                  onComplete={() => onTradeComplete(p.symbol)}
                />
              </div>
            ))}
          </div>
        )
      ) : closedCount === 0 ? (
        <p className="empty-state">
          Brak zamkniętych pozycji. Po pełnym zamknięciu (sprzedaż / cover) pozycja trafi tutaj z P/L.
        </p>
      ) : (
        <div className="data-table closed-positions-table">
          <div className="data-table-head">
            <span>Instrument</span>
            <span>Strona</span>
            <span>Ilość</span>
            <span>Wejście → Wyjście</span>
            <span>P/L (real.)</span>
            <span>Zamknięto</span>
          </div>
          {closedPositions.map((p) => (
            <Link
              key={p.id}
              to={`/instrument/${encodeURIComponent(p.symbol)}`}
              className="data-table-row closed-position-row tap-target"
            >
              <div className="position-main">
                <strong className="position-symbol">{p.symbol}</strong>
                <span className="position-name">{p.name}</span>
                {formatDt(p.opened_at) && (
                  <span className="position-opened-at">Otwarto {formatDt(p.opened_at)}</span>
                )}
              </div>
              <span className={p.is_short ? 'side-sell' : 'side-buy'}>
                {p.is_short ? 'SHORT' : 'LONG'}
              </span>
              <span className="tabular">{p.quantity}</span>
              <span className="tabular closed-position-prices">
                {p.entry_price_native.toLocaleString('pl-PL')} → {p.exit_price_native.toLocaleString('pl-PL')}{' '}
                {p.currency}
                <em>
                  {formatPln(p.entry_price_pln)} → {formatPln(p.exit_price_pln)}/szt.
                </em>
              </span>
              <span
                className={`position-pnl tabular ${p.realized_pnl_pln >= 0 ? 'positive' : 'negative'}`}
              >
                {p.realized_pnl_pln >= 0 ? '+' : ''}
                {formatPln(p.realized_pnl_pln)}
                <em>{p.realized_pnl_pct}%</em>
              </span>
              <span className="trade-time">{formatDt(p.closed_at)}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
