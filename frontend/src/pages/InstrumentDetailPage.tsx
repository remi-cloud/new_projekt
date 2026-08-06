import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchMarketAssessment, fetchSuperOpportunity } from '../api'
import { AskAgentButton } from '../components/AskAgentButton'
import { BrokerPurchaseHint } from '../components/BrokerPurchaseHint'
import { InstrumentPanel } from '../components/InstrumentPanel'
import LiquidationHeatmapBar from '../components/LiquidationHeatmap'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import { formatPrice } from '../lib/labels'
import { positionPath } from '../lib/routes'
import type { AssetCycleAssessment, SuperOpportunity } from '../types'

export function InstrumentDetailPage() {
  const { symbol: encoded } = useParams()
  const symbol = encoded ? decodeURIComponent(encoded) : ''
  const navigate = useNavigate()
  const { t } = useLocale()
  const { data, error, reload, loading } = useDashboardContext()
  const [item, setItem] = useState<AssetCycleAssessment | null>(null)
  const [itemLoading, setItemLoading] = useState(true)
  const [itemError, setItemError] = useState<string | null>(null)
  const [desk, setDesk] = useState<SuperOpportunity | null>(null)

  const cached = useMemo(
    () => data?.market_assessments.find((a) => a.symbol === symbol) ?? null,
    [data, symbol],
  )

  useEffect(() => {
    if (!symbol) return
    if (cached) {
      setItem(cached)
      setItemLoading(false)
      setItemError(null)
      return
    }

    let cancelled = false
    setItemLoading(true)
    setItemError(null)
    void fetchMarketAssessment(symbol)
      .then((assessment) => {
        if (!cancelled) {
          setItem(assessment)
          setItemError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setItem(null)
          setItemError(formatThrownError(err, t('instrument.notFound', { symbol })))
        }
      })
      .finally(() => {
        if (!cancelled) setItemLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [symbol, cached, t])

  useEffect(() => {
    if (!symbol) return
    let cancelled = false
    setDesk(null)
    void fetchSuperOpportunity(symbol)
      .then((row) => {
        if (!cancelled) setDesk(row)
      })
      .catch(() => {
        if (!cancelled) setDesk(null)
      })
    return () => {
      cancelled = true
    }
  }, [symbol])

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if ((loading && !data) || itemLoading) return <Loading message={t('layout.loading')} />

  if (itemError || !item) {
    return (
      <div className="empty-state">
        <p>{itemError ?? t('instrument.notFound', { symbol })}</p>
        <button type="button" className="btn btn-primary tap-target" onClick={() => navigate('/rynki')}>
          {t('instrument.backToMarkets')}
        </button>
      </div>
    )
  }

  const limited = item.confidence === 0

  return (
    <div className="instrument-detail institutional-page">
      <header className="detail-header">
        <button type="button" className="back-btn tap-target" onClick={() => navigate(-1)}>
          {t('instrument.backMarkets')}
        </button>
        <div className="detail-header-meta">
          <span className="detail-eyebrow">{t('instrument.eyebrow')}</span>
          <h1 className="detail-title">{item.symbol}</h1>
          <p className="detail-subtitle">{item.name}</p>
          {limited && <p className="detail-limited-hint">{t('instrument.limitedData')}</p>}
          <div className="macro-news-agent-row" style={{ marginTop: 10 }}>
            <AskAgentButton mode="instrument" symbol={item.symbol} name={item.name} />
          </div>
        </div>
      </header>
      <BrokerPurchaseHint info={item.broker_info} />

      {desk && (
        <section className="instrument-desk" aria-label="Bid Ask Heatmapa">
          <div className="section-header" style={{ marginBottom: 8 }}>
            <h2 className="section-title">Order book · heatmapa</h2>
            <Link to={positionPath(desk.symbol)} className="link-btn tap-target card-nav-link">
              Superokazje →
            </Link>
          </div>
          <div className="book-strip">
            <div className="super-grid">
              <div className="stat bid-stat">
                <div className="stat-label">Bid</div>
                <div className="stat-value">
                  {desk.bid != null ? formatPrice(desk.bid, desk.asset_class) : '—'}
                </div>
              </div>
              <div className="stat ask-stat">
                <div className="stat-label">Ask</div>
                <div className="stat-value">
                  {desk.ask != null ? formatPrice(desk.ask, desk.asset_class) : '—'}
                </div>
              </div>
              <div className="stat">
                <div className="stat-label">Spread</div>
                <div className="stat-value">
                  {desk.spread_pct != null ? `${desk.spread_pct.toFixed(3)}%` : '—'}
                </div>
              </div>
              <div className="stat">
                <div className="stat-label">Mid</div>
                <div className="stat-value">{formatPrice(desk.price, desk.asset_class)}</div>
              </div>
            </div>
            {desk.bid != null && desk.ask != null && (
              <div className="bidask-compare">
                <div className="bidask-bar" aria-hidden>
                  <div className="bidask-bid" style={{ flex: 1 }} />
                  <div className="bidask-spread" />
                  <div className="bidask-ask" style={{ flex: 1 }} />
                </div>
                <div className="bidask-labels">
                  <span>BID {formatPrice(desk.bid, desk.asset_class)}</span>
                  <span>
                    spread {desk.spread_pct != null ? `${desk.spread_pct.toFixed(3)}%` : '—'}
                  </span>
                  <span>ASK {formatPrice(desk.ask, desk.asset_class)}</span>
                </div>
              </div>
            )}
          </div>
          <h3 className="mini-title">Heatmapa likwidacji · {desk.symbol}</h3>
          <LiquidationHeatmapBar
            heatmap={desk.heatmap}
            entry={desk.levels?.entry}
            stop={desk.levels?.stop_loss}
            tp1={desk.levels?.take_profit_1}
            tp2={desk.levels?.take_profit_2}
            prediction={desk.prediction}
          />
        </section>
      )}

      <InstrumentPanel item={item} expanded />
    </div>
  )
}
