import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchRoiShowcase } from '../api'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError, resolveApiMessage } from '../i18n/utils'
import type { RoiShowcaseResult } from '../types'

function fmtMoney(n: number, locale: string): string {
  return n.toLocaleString(locale, { maximumFractionDigits: 0 })
}

function fmtPct(n: number): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

export function InvestmentShowcase() {
  const { t, dateLocale } = useLocale()
  const [data, setData] = useState<RoiShowcaseResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchRoiShowcase()
      setData(result)
    } catch (err) {
      setError(formatThrownError(err, resolveApiMessage('roiShowcaseFailed')))
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return <div className="investment-showcase investment-showcase-loading">{t('investmentShowcase.loading')}</div>
  }
  if (error || !data) {
    return (
      <div className="investment-showcase investment-showcase-error">
        <p>{error ?? t('investmentShowcase.error')}</p>
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
            {t('investmentShowcase.strategyLabel')}: <strong>{data.strategy}</strong>
          </span>
        </div>
      </header>

      <div className="investment-showcase-grid">
        {data.cards.map((card) => (
          <article
            key={card.id}
            className={`investment-showcase-card ${card.featured ? 'featured' : ''}`}
          >
            {card.featured && <span className="investment-showcase-badge">{t('investmentShowcase.featured')}</span>}
            <h3>{card.name}</h3>
            <p className="investment-showcase-symbol">{card.symbol}</p>
            <div className="investment-showcase-stat">
              <span>{t('investmentShowcase.finalValue')}</span>
              <strong className={card.profit >= 0 ? 'pos' : 'neg'}>
                {fmtMoney(card.final_value, dateLocale)} USD
              </strong>
            </div>
            <div className="investment-showcase-stat">
              <span>{t('investmentShowcase.profit')}</span>
              <strong className={card.profit >= 0 ? 'pos' : 'neg'}>
                {fmtMoney(card.profit, dateLocale)} USD
              </strong>
            </div>
            <div className="investment-showcase-stat">
              <span>{t('investmentShowcase.roi')}</span>
              <strong className={card.roi_pct >= 0 ? 'pos' : 'neg'}>{fmtPct(card.roi_pct)}</strong>
            </div>
            {card.buy_hold && (
              <p className="investment-showcase-bh">
                {t('investmentShowcase.vsBuyHold', { n: card.buy_hold.roi_pct.toFixed(1) })}
              </p>
            )}
          </article>
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
