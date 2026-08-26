import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchFomoEvents, type FomoEvent } from '../api'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'

function shortMint(mint: string): string {
  if (!mint || mint.length < 10) return mint
  return `${mint.slice(0, 4)}…${mint.slice(-4)}`
}

function formatUsd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  if (Math.abs(n) >= 1000) return `$${Math.round(n).toLocaleString()}`
  return `$${n.toFixed(0)}`
}

export function FomoGhostStrip() {
  const { t, dateLocale } = useLocale()
  const [events, setEvents] = useState<FomoEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetchFomoEvents(12, 'buy')
      .then((d) => {
        setEvents(d.events || [])
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'fomo error'))
  }, [])

  useEffect(() => {
    load()
    const id = window.setInterval(load, 60_000)
    return () => window.clearInterval(id)
  }, [load])

  useLiveFeed((ev) => {
    if (ev.type === 'fomo_tick') load()
  })

  return (
    <section className="dashboard-section fomo-ghost-strip">
      <div className="section-header">
        <h2 className="section-title">{t('fomo.stripTitle')}</h2>
        <div className="telemetry-chips">
          <span className="pres-season-chip season-best_six">{t('fomo.stripLive')}</span>
          <Link to="/fomo" className="link-btn tap-target card-nav-link">
            {t('fomo.openDesk')}
          </Link>
        </div>
      </div>
      <p className="page-lead">{t('fomo.stripLead')}</p>
      {error && <p className="empty-state">{error}</p>}
      {!error && events.length === 0 && <p className="empty-state">{t('fomo.stripEmpty')}</p>}
      {events.length > 0 && (
        <ul className="fomo-strip-feed">
          {events.slice(0, 8).map((ev) => (
            <li key={ev.event_id} className="fomo-strip-item">
              <span className="fomo-strip-buy">{t('fomo.bagIn')}</span>
              <strong>@{ev.handle}</strong>
              <span className="fomo-strip-token">
                {ev.symbol} <em>{shortMint(ev.mint)}</em>
              </span>
              <span className="fomo-strip-usd">{formatUsd(ev.usd_amount)}</span>
              <span className="fomo-strip-chain">{ev.chain}</span>
              <span className="fomo-strip-time">
                {ev.ts_unix
                  ? new Date(ev.ts_unix * 1000).toLocaleTimeString(dateLocale, {
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '—'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
