import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchFomoEvents,
  fetchFomoFamily,
  fetchFomoStatus,
  fetchFomoTop,
  registerFomoKey,
  runFomoTick,
  type FomoBag,
  type FomoEvent,
  type FomoStatus,
  type FomoTrader,
} from '../api'
import { FomoGhostStrip } from '../components/FomoGhostStrip'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'
import { formatThrownError } from '../i18n/utils'

function shortMint(mint: string): string {
  if (!mint || mint.length < 12) return mint
  return `${mint.slice(0, 6)}…${mint.slice(-4)}`
}

function formatUsd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return `$${Math.round(n).toLocaleString()}`
}

export function FomoGhostPage() {
  const { t, dateLocale } = useLocale()
  const [status, setStatus] = useState<FomoStatus | null>(null)
  const [traders, setTraders] = useState<FomoTrader[]>([])
  const [events, setEvents] = useState<FomoEvent[]>([])
  const [bags, setBags] = useState<FomoBag[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [st, top, ev, fam] = await Promise.all([
        fetchFomoStatus(),
        fetchFomoTop(30),
        fetchFomoEvents(80, 'buy'),
        fetchFomoFamily(80),
      ])
      setStatus(st)
      setTraders(top.traders || [])
      setEvents(ev.events || [])
      setBags(fam.bags || [])
    } catch (err) {
      setError(formatThrownError(err, t('fomo.loadError')))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 60_000)
    return () => window.clearInterval(id)
  }, [load])

  useLiveFeed((ev) => {
    if (ev.type === 'fomo_tick') void load()
  })

  const onRun = async () => {
    setRunning(true)
    try {
      await runFomoTick(true)
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('fomo.runError')))
    } finally {
      setRunning(false)
    }
  }

  const onRegister = async () => {
    setRegistering(true)
    try {
      await registerFomoKey()
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('fomo.registerError')))
    } finally {
      setRegistering(false)
    }
  }

  if (loading && !status) return <Loading message={t('fomo.loading')} />
  if (error && !status) return <ErrorState message={error} onRetry={() => void load()} />

  return (
    <div className="fomo-page">
      <header className="pearl-header">
        <span className="page-eyebrow">{t('fomo.eyebrow')}</span>
        <h1 className="page-title">{t('fomo.title')}</h1>
        <p className="pearl-lead">{t('fomo.lead')}</p>
        <div className="pearl-status-bar">
          <span
            className={`pearl-live-pill ${status?.enabled || status?.mode === 'degraded' ? 'on' : ''} ${
              status?.mode === 'degraded' || status?.needs_api_key ? 'warn' : ''
            }`}
          >
            {status?.mode === 'degraded'
              ? t('fomo.degraded')
              : status?.needs_api_key
                ? t('fomo.needsKey')
                : status?.enabled
                  ? t('fomo.scanning')
                  : t('fomo.disabled')}
          </span>
          <span className="pearl-meta">
            {t('fomo.meta', {
              n: status?.traders_count ?? traders.length,
              e: status?.events_count ?? events.length,
            })}
            {status?.last_tick_at
              ? ` · ${t('fomo.lastTick', {
                  date: new Date(status.last_tick_at).toLocaleString(dateLocale),
                })}`
              : ''}
          </span>
          {(status?.needs_api_key || status?.mode === 'degraded') && (
            <button
              type="button"
              className="btn tap-target"
              onClick={() => void onRegister()}
              disabled={registering}
            >
              {registering ? t('fomo.registering') : t('fomo.register')}
            </button>
          )}
          <button
            type="button"
            className="btn btn-primary tap-target"
            onClick={() => void onRun()}
            disabled={running}
          >
            {running ? t('fomo.running') : t('fomo.runNow')}
          </button>
        </div>
        {status?.last_error && <p className="pearl-agent-error">{status.last_error}</p>}
        {status?.mode === 'degraded' && <p className="pres-next-term-note">{t('fomo.degradedHint')}</p>}
        {status?.needs_api_key && status?.mode !== 'degraded' && (
          <p className="pres-next-term-note">{t('fomo.keyHint')}</p>
        )}
        {status?.telegram && (
          <p className="pres-next-term-note">
            {t('fomo.telegramMeta', {
              mode: status.telegram.listen_mode || '—',
              n: status.telegram.configured_chats?.length ?? 0,
            })}
          </p>
        )}
      </header>

      <FomoGhostStrip />

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('fomo.familyTitle')}</h2>
        </div>
        <p className="pearl-lead">
          {t('fomo.familyLead', {
            open: status?.family?.positions_open ?? bags.length,
            all: status?.family?.positions_all ?? bags.length,
          })}{' '}
          <Link to="/axiom">{t('fomo.openAxiom')}</Link>
        </p>
        {bags.length === 0 ? (
          <p className="empty-state">{t('fomo.familyEmpty')}</p>
        ) : (
          <div className="fomo-table-wrap">
            <table className="fomo-table">
              <thead>
                <tr>
                  <th>{t('fomo.colHandle')}</th>
                  <th>{t('fomo.colSymbol')}</th>
                  <th>{t('fomo.colNet')}</th>
                  <th>{t('fomo.colMint')}</th>
                  <th>{t('fomo.colChain')}</th>
                </tr>
              </thead>
              <tbody>
                {bags.map((b) => (
                  <tr key={`${b.handle}-${b.mint}`}>
                    <td>
                      <strong>@{b.handle}</strong>
                    </td>
                    <td>{b.symbol}</td>
                    <td>{formatUsd(b.net_usd)}</td>
                    <td>
                      <code className="fomo-event-mint">{shortMint(b.mint)}</code>
                    </td>
                    <td>{b.chain}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('fomo.topTitle')}</h2>
        </div>
        {traders.length === 0 ? (
          <p className="empty-state">{t('fomo.topEmpty')}</p>
        ) : (
          <div className="fomo-table-wrap">
            <table className="fomo-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{t('fomo.colHandle')}</th>
                  <th>PnL</th>
                  <th>{t('fomo.colWin')}</th>
                  <th>{t('fomo.colTrades')}</th>
                </tr>
              </thead>
              <tbody>
                {traders.map((tr) => (
                  <tr key={tr.handle}>
                    <td>{tr.rank}</td>
                    <td>
                      <strong>@{tr.handle}</strong>
                    </td>
                    <td>{tr.pnl != null ? formatUsd(tr.pnl) : '—'}</td>
                    <td>{tr.win_rate != null ? `${tr.win_rate.toFixed(0)}%` : '—'}</td>
                    <td>{tr.trades ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('fomo.feedTitle')}</h2>
        </div>
        {events.length === 0 ? (
          <p className="empty-state">{t('fomo.feedEmpty')}</p>
        ) : (
          <ul className="fomo-event-list">
            {events.map((ev) => (
              <li key={ev.event_id} className="fomo-event-card">
                <div className="fomo-event-head">
                  <span className="fomo-strip-buy">{t('fomo.bagIn')}</span>
                  <strong>@{ev.handle}</strong>
                  <span className="fomo-strip-time">
                    {ev.ts_unix
                      ? new Date(ev.ts_unix * 1000).toLocaleString(dateLocale)
                      : ev.created_at
                        ? new Date(ev.created_at).toLocaleString(dateLocale)
                        : '—'}
                  </span>
                </div>
                <div className="fomo-event-body">
                  <span className="fomo-event-symbol">{ev.symbol}</span>
                  <code className="fomo-event-mint">{shortMint(ev.mint)}</code>
                  <span>{formatUsd(ev.usd_amount)}</span>
                  <span className="fomo-strip-chain">{ev.chain}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="pres-next-term-note">{t('fomo.disclaimer')}</p>
    </div>
  )
}
