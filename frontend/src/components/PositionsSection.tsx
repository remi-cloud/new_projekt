import { Link } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import { PaperClosedPosition, PaperLimitOrder, PaperPosition, PaperTrade } from '../types'
import { formatPln } from '../utils/format'
import { BrokerPurchaseHint } from './BrokerPurchaseHint'
import { AskAgentButton } from './AskAgentButton'
import { CoinAvatar } from './CoinAvatar'
import { CommunityActions } from './CommunityActions'
import { InstrumentShareMenu } from './InstrumentShareMenu'
import { PositionTradeControl } from './PositionTradeControl'

export type PositionsTab = 'open' | 'closed' | 'history'

interface PositionsSectionProps {
  tab: PositionsTab
  onTabChange: (tab: PositionsTab) => void
  openCount: number
  closedCount: number
  historyCount: number
  positions: PaperPosition[]
  closedPositions: PaperClosedPosition[]
  recentTrades: PaperTrade[]
  openOrders: PaperLimitOrder[]
  tradingSymbol: string | null
  onTradeComplete: (symbol: string) => Promise<void>
}

export function PositionsSection({
  tab,
  onTabChange,
  openCount,
  closedCount,
  historyCount,
  positions,
  closedPositions,
  recentTrades,
  openOrders,
  tradingSymbol,
  onTradeComplete,
}: PositionsSectionProps) {
  const { t, dateLocale } = useLocale()

  const formatDt = (iso?: string): string | null => {
    if (!iso) return null
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return null
    return d.toLocaleString(dateLocale)
  }

  const formatQty = (qty: number): string => {
    const abs = Math.abs(qty)
    if (abs >= 1) return abs.toLocaleString(dateLocale, { maximumFractionDigits: 4 })
    return abs.toPrecision(4)
  }

  return (
    <section className="portfolio-section positions-section">
      <div className="section-header">
        <div className="section-header-left">
          <h3 className="section-title">{t('positions.title')}</h3>
          <div className="position-tabs" role="tablist" aria-label={t('positions.tabsAria')}>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'open'}
              className={`position-tab ${tab === 'open' ? 'active' : ''}`}
              onClick={() => onTabChange('open')}
            >
              {t('positions.open')}
              <span className="position-tab-count">{openCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'closed'}
              className={`position-tab ${tab === 'closed' ? 'active' : ''}`}
              onClick={() => onTabChange('closed')}
            >
              {t('positions.closed')}
              <span className="position-tab-count">{closedCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'history'}
              className={`position-tab ${tab === 'history' ? 'active' : ''}`}
              onClick={() => onTabChange('history')}
            >
              {t('positions.history')}
              <span className="position-tab-count">{historyCount}</span>
            </button>
          </div>
        </div>
      </div>

      {tab === 'open' ? (
        openCount === 0 ? (
          <p className="empty-state">{t('positions.emptyOpen')}</p>
        ) : (
          <div className="data-table positions-table">
            <div className="data-table-head">
              <span>{t('table.instrument')}</span>
              <span>{t('table.quantity')}</span>
              <span>{t('table.value')}</span>
              <span>{t('table.pnlUnrealized')}</span>
              <span aria-hidden />
            </div>
            {positions.map((p) => (
              <div key={p.symbol} className="data-table-row position-row">
                <Link
                  to={`/instrument/${encodeURIComponent(p.symbol)}`}
                  className="position-row-link tap-target"
                >
                  <div className="position-main">
                    <div className="position-identity">
                      <CoinAvatar symbol={p.symbol} name={p.name} imageUrl={p.image_url} />
                      <div className="position-identity-text">
                        <strong className="position-symbol">{p.symbol}</strong>
                        <span className="position-name">{p.name}</span>
                      </div>
                    </div>
                    {formatDt(p.opened_at) && (
                      <span className="position-opened-at">
                        {t('positions.opened', { date: formatDt(p.opened_at)! })}
                      </span>
                    )}
                    <BrokerPurchaseHint info={p.broker_info} compact />
                    <div className="dash-agent-actions" onClick={(e) => e.stopPropagation()}>
                      <AskAgentButton mode="instrument" symbol={p.symbol} name={p.name} compact />
                      <CommunityActions symbol={p.symbol} name={p.name} compact />
                      <InstrumentShareMenu
                        symbol={p.symbol}
                        name={p.name}
                        kind="position"
                        side={p.is_short ? t('common.short') : t('common.long')}
                        pnlPct={p.unrealized_pnl_pct}
                        compact
                      />
                    </div>
                  </div>
                  <span className="position-qty tabular">
                    {p.is_short ? `${t('common.short')} ${formatQty(p.quantity)}` : formatQty(p.quantity)}
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
                  onClosed={() => onTabChange('history')}
                />
              </div>
            ))}
          </div>
        )
      ) : tab === 'closed' ? (
        closedCount === 0 ? (
          <p className="empty-state">{t('positions.emptyClosed')}</p>
        ) : (
          <div className="data-table closed-positions-table">
            <div className="data-table-head">
              <span>{t('table.instrument')}</span>
              <span>{t('table.side')}</span>
              <span>{t('table.quantity')}</span>
              <span>{t('table.entryExit')}</span>
              <span>{t('table.pnlRealized')}</span>
              <span>{t('table.closedAt')}</span>
            </div>
            {closedPositions.map((p) => (
              <Link
                key={p.id}
                to={`/instrument/${encodeURIComponent(p.symbol)}`}
                className="data-table-row closed-position-row tap-target"
              >
                <div className="position-main">
                  <div className="position-identity">
                    <CoinAvatar symbol={p.symbol} name={p.name} imageUrl={p.image_url} />
                    <div className="position-identity-text">
                      <strong className="position-symbol">{p.symbol}</strong>
                      <span className="position-name">{p.name}</span>
                    </div>
                  </div>
                  {formatDt(p.opened_at) && (
                    <span className="position-opened-at">
                      {t('positions.opened', { date: formatDt(p.opened_at)! })}
                    </span>
                  )}
                  <div className="dash-agent-actions closed-position-share" onClick={(e) => e.stopPropagation()}>
                    <AskAgentButton mode="instrument" symbol={p.symbol} name={p.name} compact />
                    <CommunityActions symbol={p.symbol} name={p.name} compact />
                    <InstrumentShareMenu
                      symbol={p.symbol}
                      name={p.name}
                      kind="position"
                      side={p.is_short ? t('common.short') : t('common.long')}
                      pnlPct={p.realized_pnl_pct}
                      compact
                    />
                  </div>
                </div>
                <span className={p.is_short ? 'side-sell' : 'side-buy'}>
                  {p.is_short ? t('common.short') : t('common.long')}
                </span>
                <span className="tabular">{p.quantity}</span>
                <span className="tabular closed-position-prices">
                  {p.entry_price_native.toLocaleString(dateLocale)} → {p.exit_price_native.toLocaleString(dateLocale)}{' '}
                  {p.currency}
                  <em>
                    {formatPln(p.entry_price_pln)} → {formatPln(p.exit_price_pln)}
                    {t('table.perUnit')}
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
        )
      ) : historyCount === 0 ? (
        <p className="empty-state">{t('positions.emptyHistory')}</p>
      ) : (
        <div className="data-table trades-table positions-history-table">
          <div className="data-table-head">
            <span>{t('portfolio.tableSide')}</span>
            <span>{t('portfolio.tableSymbol')}</span>
            <span>{t('portfolio.tableQty')}</span>
            <span>{t('portfolio.tableAmount')}</span>
            <span>{t('portfolio.tableTime')}</span>
          </div>
          {recentTrades.map((trade) => (
            <div key={trade.id} className="data-table-row trade-row">
              <span className={`side-${trade.side}`}>
                {trade.side === 'buy' ? t('portfolio.buySide') : t('portfolio.sellSide')}
              </span>
              <span className="trade-symbol">{trade.symbol}</span>
              <span className="tabular">{trade.quantity}</span>
              <span className="tabular">{formatPln(trade.total_pln)}</span>
              <span className="trade-time">{formatDt(trade.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
