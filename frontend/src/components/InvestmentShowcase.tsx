import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchRoiShowcase } from '../api'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError, resolveApiMessage } from '../i18n/utils'
import type { RoiShowcaseCard, RoiShowcaseResult } from '../types'
import { DataStamp } from './DataStamp'

function fmtMoney(n: number, locale: string): string {
  return n.toLocaleString(locale, { maximumFractionDigits: 0 })
}

function fmtPrice(n: number, locale: string): string {
  return n.toLocaleString(locale, { maximumFractionDigits: n >= 100 ? 0 : 2 })
}

function fmtPct(n: number): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

const DEFAULT_REFRESH_MS = 10 * 60 * 1000

function ShowcaseCard({ card }: { card: RoiShowcaseCard }) {
  const { t, dateLocale } = useLocale()
  const finalValue = card.final_value
  const profit = card.profit
  const roi = card.roi_pct
  const ok =
    card.available !== false &&
    typeof finalValue === 'number' &&
    typeof profit === 'number' &&
    typeof roi === 'number'

  return (
    <article
      className={`investment-showcase-card ${card.featured ? 'featured' : ''} ${card.stale ? 'stale' : ''}`}
      data-testid={`showcase-card-${card.id}`}
    >
      {card.featured && <span className="investment-showcase-badge">{t('investmentShowcase.featured')}</span>}
      <h3>{card.name}</h3>
      <p className="investment-showcase-symbol">{card.symbol}</p>
      {!ok ? (
        <p className="investment-showcase-nodata">{t('liveData.noData')}</p>
      ) : (
        <>
          <div className="investment-showcase-stat">
            <span>{t('investmentShowcase.finalValue')}</span>
            <strong className={profit >= 0 ? 'pos' : 'neg'}>{fmtMoney(finalValue, dateLocale)} USD</strong>
          </div>
          <div className="investment-showcase-stat">
            <span>{t('investmentShowcase.profit')}</span>
            <strong className={profit >= 0 ? 'pos' : 'neg'}>{fmtMoney(profit, dateLocale)} USD</strong>
          </div>
          <div className="investment-showcase-stat">
            <span>{t('investmentShowcase.roi')}</span>
            <strong className={roi >= 0 ? 'pos' : 'neg'}>{fmtPct(roi)}</strong>
          </div>
          {card.buy_hold && (
            <p className="investment-showcase-bh">
              {t('investmentShowcase.vsBuyHold', { n: card.buy_hold.roi_pct.toFixed(1) })} (
              {fmtMoney(card.buy_hold.final_value, dateLocale)} USD)
            </p>
          )}
          {card.data_start && card.data_end && (
            <p className="investment-showcase-meta-line">
              {t('liveData.period')}: {card.data_start} → {card.data_end}
              {typeof card.start_price === 'number' && typeof card.end_price === 'number' && (
                <>
                  {' · '}
                  {t('liveData.priceStartEnd')}: {fmtPrice(card.start_price, dateLocale)} →{' '}
                  {fmtPrice(card.end_price, dateLocale)}
                </>
              )}
              {typeof card.trades_count === 'number' && (
                <>
                  {' · '}
                  {t('liveData.trades')}: {card.trades_count}
                </>
              )}
            </p>
          )}
          {card.strategy_rules && (
            <p className="investment-showcase-rules">
              {t('liveData.rules')}: {card.strategy_rules}
            </p>
          )}
        </>
      )}
      <DataStamp source={card.source} updatedAt={card.updated_at} stale={card.stale || !ok} />
    </article>
  )
}

export function InvestmentShowcase() {
  const { t, dateLocale } = useLocale()
  const [data, setData] = useState<RoiShowcaseResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (background = false) => {
    if (!background) setLoading(true)
    setError(null)
    try {
      setData(await fetchRoiShowcase())
    } catch (err) {
      // Keep the last real payload on screen (its cards carry their own timestamps);
      // only show "brak danych" when nothing real was ever loaded.
      setError(formatThrownError(err, resolveApiMessage('roiShowcaseFailed')))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const refreshMs = data?.refresh_seconds ? data.refresh_seconds * 1000 : DEFAULT_REFRESH_MS
  useEffect(() => {
    const id = window.setInterval(() => void load(true), refreshMs)
    return () => window.clearInterval(id)
  }, [load, refreshMs])

  if (loading && !data) {
    return <div className="investment-showcase investment-showcase-loading">{t('investmentShowcase.loading')}</div>
  }
  if (!data) {
    return (
      <div className="investment-showcase investment-showcase-error">
        <p>
          {t('liveData.noData')}
          {error ? ` — ${error}` : ''}
        </p>
        <button type="button" className="btn btn-ghost tap-target" onClick={() => void load()}>
          {t('common.retry')}
        </button>
      </div>
    )
  }

  const featured = data.cards.find((c) => c.featured) ?? data.cards[0]

  return (
    <section className="investment-showcase" aria-labelledby="investment-showcase-title">
      <header className="investment-showcase-header">
        <span className="page-eyebrow">{t('investmentShowcase.eyebrow')}</span>
        <h2 id="investment-showcase-title" className="section-title">
          {t('investmentShowcase.headline')}
        </h2>
        <p className="investment-showcase-lead">{t('investmentShowcase.lead')}</p>
        <div className="investment-showcase-meta">
          <span>
            {t('investmentShowcase.amountLabel')}: <strong>{fmtMoney(data.amount, dateLocale)} USD</strong>
          </span>
          <span>
            {t('investmentShowcase.yearsLabel')}: <strong>{data.years}</strong>
          </span>
          <span>
            {t('liveData.period')}: <strong>{data.start} → {data.end}</strong>
          </span>
        </div>
        <DataStamp source={data.source} updatedAt={data.updated_at} stale={Boolean(error)} />
        {data.refresh_seconds ? (
          <p className="data-stamp">{t('liveData.refreshing', { n: Math.round(data.refresh_seconds / 60) })}</p>
        ) : null}
      </header>

      <div className="investment-showcase-grid">
        {data.cards.map((card) => (
          <ShowcaseCard key={card.id} card={card} />
        ))}
      </div>

      <div className="investment-showcase-footer">
        <Link
          to={`/kalkulator?mode=backtest&symbol=${encodeURIComponent(featured?.symbol ?? 'BTC-USD')}`}
          className="btn btn-primary tap-target"
        >
          {t('investmentShowcase.cta')}
        </Link>
        <p className="investment-showcase-disclaimer">{t('investmentShowcase.disclaimer')}</p>
      </div>
    </section>
  )
}
