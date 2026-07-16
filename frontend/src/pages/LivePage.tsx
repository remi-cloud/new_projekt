import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchPublicLive, voteWatchlist, type PublicLiveDigest } from '../api'
import { NewsletterSignup } from '../components/NewsletterSignup'
import { ErrorState } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'

export function LivePage() {
  const { t, locale, dateLocale } = useLocale()
  const { signal, phase } = useDomainLabels()
  const [data, setData] = useState<PublicLiveDigest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      setError(null)
      const res = await fetchPublicLive(locale)
      setData(res)
    } catch {
      setError(t('growth.errors.live'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 120000)
    return () => window.clearInterval(id)
  }, [locale])

  const onVote = async (symbol: string, name: string) => {
    try {
      await voteWatchlist(symbol, name)
      void load()
    } catch {
      /* ignore */
    }
  }

  if (loading && !data) return <div className="page-loading">{t('common.loading')}</div>
  if (error && !data) return <ErrorState message={error} onRetry={() => void load()} />
  if (!data) return null

  const btc = data.bitcoin_cycle

  return (
    <div className="growth-live institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('growth.liveEyebrow')}</span>
        <h2 className="page-headline">{t('growth.liveHeadline')}</h2>
        <p className="page-lead">{t('growth.liveLead')}</p>
        <div className="growth-live-actions">
          <Link className="btn tap-target" to="/kalkulator">
            {t('growth.ctaCalc')}
          </Link>
          <Link className="btn btn-ghost tap-target" to="/biznes">
            {t('growth.ctaBiz')}
          </Link>
        </div>
      </header>

      <div className="growth-status-pill">
        <span className="dot" /> {data.status.toUpperCase()} · {new Date(data.fetched_at).toLocaleString(dateLocale)}
      </div>

      <div className="growth-live-grid">
        <section className="growth-card">
          <h3>{t('growth.btcNow')}</h3>
          {btc ? (
            <>
              <p className="growth-big">
                {phase(btc.phase)} · {signal[btc.signal as keyof typeof signal] ?? btc.signal}
              </p>
              <p className="growth-meta">
                ATH {btc.last_ath_date} · ${btc.last_ath_price.toLocaleString(dateLocale)} · day {btc.days_since_ath}
              </p>
              <p className="growth-body">{btc.rationale}</p>
            </>
          ) : (
            <p className="growth-body">{t('growth.scanWait')}</p>
          )}
        </section>

        <section className="growth-card">
          <h3>{t('growth.usaNow')}</h3>
          {data.presidential_cycle ? (
            <>
              <p className="growth-big">
                {data.presidential_cycle.president} · Y{data.presidential_cycle.year_number}
              </p>
              <p className="growth-meta">
                {data.presidential_cycle.signal} · expect ~
                {data.presidential_cycle.current_year_expected_return_pct}%
              </p>
              <p className="growth-body">{data.presidential_cycle.rationale}</p>
            </>
          ) : (
            <p className="growth-body">{t('growth.scanWait')}</p>
          )}
        </section>
      </div>

      <section className="growth-section">
        <h3>{t('growth.topOpps')}</h3>
        <div className="growth-opp-list">
          {data.top_opportunities.length === 0 && <p className="growth-body">{t('growth.scanWait')}</p>}
          {data.top_opportunities.map((o) => (
            <Link key={o.symbol} to={`/instrument/${encodeURIComponent(o.symbol)}`} className="growth-opp">
              <strong>{o.symbol}</strong>
              <span>{o.action}</span>
              <span>{Math.round(o.confidence)}%</span>
              <em>{o.rationale}</em>
            </Link>
          ))}
        </div>
      </section>

      <section className="growth-section">
        <h3>{t('growth.liveNews')}</h3>
        <div className="growth-news-grid">
          {data.news.map((n) => (
            <a
              key={n.id}
              className="growth-news"
              href={n.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
            >
              {n.image_url && <img src={n.image_url} alt="" loading="lazy" />}
              <div>
                <span className="growth-cat">{n.category}</span>
                <strong>{n.title}</strong>
                <small>
                  {n.source}
                  {n.age_minutes != null ? ` · ${n.age_minutes} min` : ''}
                </small>
              </div>
            </a>
          ))}
        </div>
      </section>

      <section className="growth-section">
        <h3>{t('growth.watchlist')}</h3>
        <p className="growth-body">{t('growth.watchlistLead')}</p>
        <ul className="growth-watch">
          {data.watchlist.map((w) => (
            <li key={w.symbol}>
              <span>
                <strong>{w.symbol}</strong> {w.name}
              </span>
              <button type="button" className="tap-target" onClick={() => void onVote(w.symbol, w.name)}>
                ▲ {w.votes}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <NewsletterSignup source="live" />
      <p className="growth-disclaimer">{data.disclaimer}</p>
    </div>
  )
}
