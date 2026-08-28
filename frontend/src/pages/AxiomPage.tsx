import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchAxiomPositions,
  fetchAxiomPulse,
  fetchAxiomStatus,
  runAxiomTick,
  type AxiomPosition,
  type AxiomPulseMarket,
  type AxiomStatus,
} from '../api'
import { CoinAvatar } from '../components/CoinAvatar'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'
import { formatThrownError } from '../i18n/utils'
import { memeDexScreenerUrl, memeTerminalUrl } from '../lib/memeTerminalUrl'

function shortMint(mint: string): string {
  if (!mint || mint.length < 12) return mint
  return `${mint.slice(0, 6)}…${mint.slice(-4)}`
}

function formatUsd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1000) return `$${Math.round(n).toLocaleString()}`
  return `$${n.toFixed(0)}`
}

function formatPct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

export function AxiomPage() {
  const { t, dateLocale } = useLocale()
  const [status, setStatus] = useState<AxiomStatus | null>(null)
  const [pulse, setPulse] = useState<AxiomPulseMarket[]>([])
  const [positions, setPositions] = useState<AxiomPosition[]>([])
  const [posFilter, setPosFilter] = useState<'all' | 'open' | 'closed'>('all')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [st, p, pos] = await Promise.all([
        fetchAxiomStatus(),
        fetchAxiomPulse(80),
        fetchAxiomPositions(200, posFilter),
      ])
      setStatus(st)
      setPulse(p.markets || [])
      setPositions(pos.positions || [])
    } catch (err) {
      setError(formatThrownError(err, t('axiom.loadError')))
    } finally {
      setLoading(false)
    }
  }, [t, posFilter])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 90_000)
    return () => window.clearInterval(id)
  }, [load])

  useLiveFeed((ev) => {
    if (ev.type === 'axiom_tick' || ev.type === 'fomo_tick') void load()
  })

  const onRun = async () => {
    setRunning(true)
    try {
      await runAxiomTick()
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('axiom.runError')))
    } finally {
      setRunning(false)
    }
  }

  if (loading && !status) return <Loading message={t('axiom.loading')} />
  if (error && !status) return <ErrorState message={error} onRetry={() => void load()} />

  return (
    <div className="fomo-page axiom-page">
      <header className="pearl-header">
        <span className="page-eyebrow">{t('axiom.eyebrow')}</span>
        <h1 className="page-title">{t('axiom.title')}</h1>
        <p className="pearl-lead">{t('axiom.lead')}</p>
        <div className="pearl-status-bar">
          <span className={`pearl-live-pill ${status?.enabled ? 'on' : ''}`}>
            {status?.enabled ? t('axiom.scanning') : t('axiom.disabled')}
          </span>
          <span className="pearl-meta">
            {t('axiom.meta', {
              p: status?.pulse_count ?? pulse.length,
              o: status?.positions_open ?? 0,
              a: status?.positions_all ?? positions.length,
            })}
            {status?.last_tick_at
              ? ` · ${t('axiom.lastTick', {
                  date: new Date(status.last_tick_at).toLocaleString(dateLocale),
                })}`
              : ''}
          </span>
          <button
            type="button"
            className="btn btn-primary tap-target"
            onClick={() => void onRun()}
            disabled={running}
          >
            {running ? t('axiom.running') : t('axiom.runNow')}
          </button>
        </div>
        {status?.last_error && <p className="pearl-agent-error">{status.last_error}</p>}
        <p className="pres-next-term-note">
          {status?.axiom_auth ? t('axiom.authOn') : t('axiom.authOff')}
          {status?.wallets_tracked
            ? ` · ${t('axiom.wallets', { n: status.wallets_tracked })}`
            : ''}
          {' · '}
          <Link to="/fomo">{t('axiom.openFomo')}</Link>
        </p>
      </header>

      <section className="dashboard-section kar-digital-desk">
        <div className="section-header">
          <h2 className="section-title">{t('axiom.karTitle')}</h2>
        </div>
        {status?.kar_digital_configured ? (
          <p className="pearl-lead">
            {t('axiom.karReady', {
              w: shortMint(status.kar_digital_wallet || ''),
            })}
          </p>
        ) : (
          <p className="pres-next-term-note">{t('axiom.karHint')}</p>
        )}
        <p className="pearl-lead">
          <Link to="/portfel">{t('axiom.openPortfolio')}</Link>
        </p>
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('axiom.positionsTitle')}</h2>
          <div className="tier-filter" role="group" aria-label={t('axiom.posFilter')}>
            {(['all', 'open', 'closed'] as const).map((f) => (
              <button
                key={f}
                type="button"
                className={`btn tap-target ${posFilter === f ? 'btn-primary' : ''}`}
                onClick={() => setPosFilter(f)}
              >
                {f === 'all' ? t('axiom.filterAll') : f === 'open' ? t('axiom.filterOpen') : t('axiom.filterClosed')}
              </button>
            ))}
          </div>
        </div>
        {positions.length === 0 ? (
          <p className="empty-state">{t('axiom.positionsEmpty')}</p>
        ) : (
          <div className="fomo-table-wrap">
            <table className="fomo-table">
              <thead>
                <tr>
                  <th>{t('axiom.colOwner')}</th>
                  <th>{t('axiom.colKind')}</th>
                  <th>{t('axiom.colSymbol')}</th>
                  <th>{t('axiom.colStatus')}</th>
                  <th>{t('axiom.colSize')}</th>
                  <th>{t('axiom.colMint')}</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr key={pos.position_id}>
                    <td>
                      <strong>
                        {pos.owner_kind === 'fomo_family'
                          ? `@${pos.owner}`
                          : pos.owner_kind === 'kar_digital'
                            ? pos.owner
                            : shortMint(pos.owner)}
                      </strong>
                    </td>
                    <td>
                      {pos.owner_kind === 'fomo_family'
                        ? 'FOMO Family'
                        : pos.owner_kind === 'kar_digital'
                          ? 'Kar Digital'
                          : 'Wallet'}
                    </td>
                    <td>
                      <span className="launch-symbol-cell">
                        <CoinAvatar symbol={pos.symbol} imageUrl={pos.image_url} size={22} />
                        {pos.symbol}
                      </span>
                    </td>
                    <td>
                      <span className={pos.status === 'open' ? 'fomo-strip-buy' : ''}>
                        {pos.status}
                      </span>
                    </td>
                    <td>
                      {pos.usd_size != null
                        ? formatUsd(pos.usd_size)
                        : pos.amount != null
                          ? pos.amount.toLocaleString(dateLocale)
                          : '—'}
                    </td>
                    <td>
                      {(() => {
                        const href =
                          memeTerminalUrl({
                            mint: pos.mint,
                            symbol: pos.symbol,
                            chain: pos.chain,
                            url: pos.url,
                          }) || memeDexScreenerUrl({ mint: pos.mint, symbol: pos.symbol, chain: pos.chain })
                        return href ? (
                          <a href={href} target="_blank" rel="noreferrer">
                            {shortMint(pos.mint)}
                          </a>
                        ) : (
                          <code>{shortMint(pos.mint)}</code>
                        )
                      })()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('axiom.pulseTitle')}</h2>
        </div>
        {pulse.length === 0 ? (
          <p className="empty-state">{t('axiom.pulseEmpty')}</p>
        ) : (
          <div className="fomo-table-wrap">
            <table className="fomo-table">
              <thead>
                <tr>
                  <th>{t('axiom.colSymbol')}</th>
                  <th>{t('axiom.colChain')}</th>
                  <th>MC</th>
                  <th>Liq</th>
                  <th>1h</th>
                  <th>24h</th>
                  <th>{t('axiom.colSource')}</th>
                </tr>
              </thead>
              <tbody>
                {pulse.map((m) => (
                  <tr key={`${m.chain}-${m.mint}`}>
                    <td>
                      <span className="launch-symbol-cell">
                        <CoinAvatar symbol={m.symbol} imageUrl={m.image_url} size={22} />
                        {(() => {
                          const href =
                            memeTerminalUrl({
                              mint: m.mint,
                              symbol: m.symbol,
                              chain: m.chain,
                              pairAddress: m.pair_address,
                              url: m.url,
                              source: m.source,
                            }) ||
                            memeDexScreenerUrl({
                              mint: m.mint,
                              symbol: m.symbol,
                              chain: m.chain,
                              pairAddress: m.pair_address,
                            })
                          return href ? (
                            <a href={href} target="_blank" rel="noreferrer">
                              {m.symbol}
                            </a>
                          ) : (
                            m.symbol
                          )
                        })()}
                      </span>
                    </td>
                    <td>{m.chain}</td>
                    <td>{formatUsd(m.market_cap_usd)}</td>
                    <td>{formatUsd(m.liquidity_usd)}</td>
                    <td>{formatPct(m.change_1h)}</td>
                    <td>{formatPct(m.change_24h)}</td>
                    <td>{m.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="pres-next-term-note">{t('axiom.disclaimer')}</p>
    </div>
  )
}
