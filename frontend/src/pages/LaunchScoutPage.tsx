import { useCallback, useEffect, useState } from 'react'
import {
  fetchLaunchCandidates,
  fetchLaunchStatus,
  fetchLaunchTraderEvents,
  fetchLaunchTraders,
  fetchLaunchWhispers,
  runLaunchScoutTick,
  type LaunchCandidate,
  type LaunchStatus,
  type LaunchTrader,
  type LaunchTraderEvent,
  type MemeWhisper,
} from '../api'
import { CoinAvatar } from '../components/CoinAvatar'
import { LaunchScoutStrip } from '../components/LaunchScoutStrip'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'
import { formatThrownError } from '../i18n/utils'
import { memeDexScreenerUrl, memeLaunchpadUrl, memeTerminalUrl } from '../lib/memeTerminalUrl'

type Tier = 'seed' | 'all' | 'fresh' | 'early' | 'watch'

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

function formatAge(h: number | null | undefined): string {
  if (h == null || Number.isNaN(h)) return '—'
  if (h < 1) return `${Math.round(h * 60)}m`
  if (h < 48) return `${h.toFixed(1)}h`
  return `${(h / 24).toFixed(1)}d`
}

export function LaunchScoutPage() {
  const { t, dateLocale } = useLocale()
  const [status, setStatus] = useState<LaunchStatus | null>(null)
  const [candidates, setCandidates] = useState<LaunchCandidate[]>([])
  const [whispers, setWhispers] = useState<MemeWhisper[]>([])
  const [traders, setTraders] = useState<LaunchTrader[]>([])
  const [traderEvents, setTraderEvents] = useState<LaunchTraderEvent[]>([])
  const [tier, setTier] = useState<Tier>('seed')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [st, c, w, tr, te] = await Promise.all([
        fetchLaunchStatus(),
        fetchLaunchCandidates(tier, 80),
        fetchLaunchWhispers(24),
        fetchLaunchTraders(30),
        fetchLaunchTraderEvents(24),
      ])
      setStatus(st)
      setCandidates(c.candidates || [])
      setWhispers(w.whispers || [])
      setTraders(tr.traders || [])
      setTraderEvents(te.events || [])
    } catch (err) {
      setError(formatThrownError(err, t('launch.loadError')))
    } finally {
      setLoading(false)
    }
  }, [t, tier])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 60_000)
    return () => window.clearInterval(id)
  }, [load])

  useLiveFeed((ev) => {
    if (ev.type === 'launch_scout_tick') void load()
  })

  const onRun = async () => {
    setRunning(true)
    try {
      await runLaunchScoutTick()
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('launch.runError')))
    } finally {
      setRunning(false)
    }
  }

  if (loading && !status) return <Loading message={t('launch.loading')} />
  if (error && !status) return <ErrorState message={error} onRetry={() => void load()} />

  const counts = status?.counts || {}

  return (
    <div className="launch-page fomo-page">
      <header className="pearl-header">
        <span className="page-eyebrow">{t('launch.eyebrow')}</span>
        <h1 className="page-title">{t('launch.title')}</h1>
        <p className="pearl-lead launch-quote">{t('launch.quote')}</p>
        <p className="pearl-lead">{t('launch.lead')}</p>
        <p className="pres-next-term-note">{t('launch.seedNote')}</p>
        <div className="pearl-status-bar">
          <span className={`pearl-live-pill ${status?.enabled ? 'on' : ''}`}>
            {status?.enabled ? t('launch.scanning') : t('launch.disabled')}
          </span>
          <span className="pres-season-chip season-best_six">{t('launch.flagshipBadge')}</span>
          <span className="pearl-meta">
            {t('launch.meta', {
              s: counts.seed ?? 0,
              f: counts.fresh ?? 0,
              e: counts.early ?? 0,
              w: counts.watch ?? 0,
            })}
            {status?.last_tick_at
              ? ` · ${t('launch.lastTick', {
                  date: new Date(status.last_tick_at).toLocaleString(dateLocale),
                })}`
              : ''}
          </span>
          <button type="button" className="btn btn-primary tap-target" onClick={() => void onRun()} disabled={running}>
            {running ? t('launch.running') : t('launch.runNow')}
          </button>
        </div>
        <div className="telemetry-chips launch-source-chips">
          <span className="pres-season-chip">Seed</span>
          <span className="pres-season-chip">DEX</span>
          <span className="pres-season-chip">Pump</span>
          <span className="pres-season-chip">BNB</span>
          <span className="pres-season-chip">4meme</span>
          <span className="pres-season-chip">Flap</span>
          <span className="pres-season-chip">PancakeSwap</span>
          <span className="pres-season-chip">{t('launch.tradersChip')}</span>
          <span className="pres-season-chip">Gecko</span>
          <span className="pres-season-chip">Binance radar</span>
          <span className="pres-season-chip">{t('launch.whispersChip')}</span>
        </div>
        {status?.last_error && <p className="pearl-agent-error">{status.last_error}</p>}
        <p className="pres-next-term-note">{t('launch.cexNote')}</p>
      </header>

      <LaunchScoutStrip />

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('launch.tradersTitle')}</h2>
          <span className="pearl-meta">{t('launch.tradersMeta', { n: traders.length })}</span>
        </div>
        {traders.length === 0 ? (
          <p className="empty-state">{t('launch.tradersEmpty')}</p>
        ) : (
          <ul className="fomo-strip-feed launch-whisper-feed">
            {traders.slice(0, 12).map((tr) => (
              <li key={tr.wallet} className="fomo-strip-item">
                <span className="fomo-strip-buy">#{tr.rank}</span>
                <code className="fomo-event-mint">{shortMint(tr.wallet)}</code>
                <span className="fomo-strip-usd">{tr.buys ?? 0} buys</span>
                <span className="fomo-strip-chain">{tr.source || 'pump'}</span>
              </li>
            ))}
          </ul>
        )}
        {traderEvents.length > 0 && (
          <>
            <h3 className="section-title" style={{ marginTop: '1rem' }}>
              {t('launch.traderEventsTitle')}
            </h3>
            <ul className="fomo-strip-feed">
              {traderEvents.slice(0, 10).map((ev) => (
                <li key={ev.event_id} className="fomo-strip-item">
                  <span className="fomo-strip-buy">{ev.action}</span>
                  <strong>{ev.symbol}</strong>
                  <span className="fomo-strip-usd">{formatUsd(ev.usd_amount)}</span>
                  <code className="fomo-event-mint">{shortMint(ev.wallet)}</code>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('launch.whispersTitle')}</h2>
          <span className="pearl-meta">{t('launch.whispersMeta', { n: whispers.length })}</span>
        </div>
        {whispers.length === 0 ? (
          <p className="empty-state">{t('launch.whispersEmpty')}</p>
        ) : (
          <ul className="fomo-strip-feed launch-whisper-feed">
            {whispers.slice(0, 12).map((w) => (
              <li key={w.id} className="fomo-strip-item">
                <span className="fomo-strip-buy">
                  {w.author === 'elon' ? t('launch.authorElon') : t('launch.authorCz')}
                </span>
                <span className="fomo-strip-token">{(w.text || '').slice(0, 140)}</span>
                {(w.keywords || []).slice(0, 4).map((k) => (
                  <span key={k} className="fomo-strip-chain">
                    {k}
                  </span>
                ))}
                {w.url ? (
                  <a href={w.url} target="_blank" rel="noreferrer" className="link-btn">
                    →
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="filter-chips launch-tier-chips" role="tablist" aria-label={t('launch.tierFilter')}>
        {(
          [
            ['seed', 'launch.tierSeed'],
            ['fresh', 'launch.tierFresh'],
            ['early', 'launch.tierEarly'],
            ['watch', 'launch.tierWatch'],
            ['all', 'launch.tierAll'],
          ] as const
        ).map(([key, labelKey]) => (
          <button
            key={key}
            type="button"
            className={`chip tap-target ${tier === key ? 'active' : ''}`}
            onClick={() => setTier(key)}
          >
            {t(labelKey)}
            {key !== 'all' ? ` (${counts[key] ?? 0})` : ''}
          </button>
        ))}
      </div>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('launch.tableTitle')}</h2>
        </div>
        {error && <p className="pearl-agent-error">{error}</p>}
        {candidates.length === 0 ? (
          <p className="empty-state">{t('launch.empty')}</p>
        ) : (
          <div className="fomo-table-wrap">
            <table className="fomo-table">
              <thead>
                <tr>
                  <th>{t('launch.colSymbol')}</th>
                  <th>{t('launch.colChain')}</th>
                  <th>{t('launch.colDex')}</th>
                  <th>MC</th>
                  <th>{t('launch.colLiq')}</th>
                  <th>{t('launch.colAge')}</th>
                  <th>{t('launch.colTier')}</th>
                  <th>{t('launch.colTags')}</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => {
                  const term =
                    memeTerminalUrl({
                      mint: c.mint,
                      symbol: c.symbol,
                      chain: c.chain,
                      pairAddress: c.pair_address,
                      url: c.url,
                      source: c.source,
                      dexId: c.dex_id,
                    }) || c.url || null
                  const dex = memeDexScreenerUrl({
                    mint: c.mint,
                    symbol: c.symbol,
                    chain: c.chain,
                    pairAddress: c.pair_address,
                  })
                  const launchpad =
                    c.launchpad_url ||
                    memeLaunchpadUrl({
                      mint: c.mint,
                      symbol: c.symbol,
                      chain: c.chain,
                      source: c.source,
                      dexId: c.dex_id,
                      url: c.url,
                    }) ||
                    null
                  return (
                  <tr key={c.candidate_id}>
                    <td>
                      <div className="launch-symbol-cell">
                        <CoinAvatar symbol={c.symbol} name={c.name} imageUrl={c.image_url} size={32} />
                        <div>
                          {term ? (
                            <a
                              href={term}
                              target="_blank"
                              rel="noreferrer"
                              className="link-btn launch-terminal-link"
                              title={t('launch.openTerminal')}
                            >
                              <strong>{c.symbol}</strong>
                            </a>
                          ) : (
                            <strong>{c.symbol}</strong>
                          )}
                          <div>
                            <code className="fomo-event-mint">{shortMint(c.mint)}</code>
                          </div>
                          <div className="launch-terminal-links">
                            {term ? (
                              <a href={term} target="_blank" rel="noreferrer" className="link-btn">
                                {t('launch.openTerminal')}
                              </a>
                            ) : null}
                            {dex ? (
                              <a href={dex} target="_blank" rel="noreferrer" className="link-btn">
                                {t('launch.openDex')}
                              </a>
                            ) : null}
                            {launchpad ? (
                              <a href={launchpad} target="_blank" rel="noreferrer" className="link-btn">
                                {t('launch.openLaunchpad')}
                              </a>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>{c.chain}</td>
                    <td>{c.dex_id || '—'}</td>
                    <td>{formatUsd(c.market_cap)}</td>
                    <td>{formatUsd(c.liq_usd)}</td>
                    <td>{formatAge(c.age_hours)}</td>
                    <td>
                      <span className={`pres-season-chip season-best_six launch-tier-${c.tier}`}>{c.tier}</span>
                    </td>
                    <td>{(c.tags || []).join(', ') || '—'}</td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="pres-next-term-note">{t('launch.disclaimer')}</p>
    </div>
  )
}
