import { useCallback, useEffect, useState } from 'react'
import {
  fetchDexArena,
  fetchLaunchCandidates,
  fetchLaunchStatus,
  fetchLaunchTraderEvents,
  fetchLaunchTraders,
  fetchLaunchWhispers,
  fetchSessionClock,
  runLaunchScoutTick,
  type DexArenaSnapshot,
  type LaunchCandidate,
  type LaunchStatus,
  type LaunchTrader,
  type LaunchTraderEvent,
  type MemeWhisper,
  type SessionClockSnapshot,
} from '../api'
import { CoinAvatar } from '../components/CoinAvatar'
import { LaunchScoutStrip } from '../components/LaunchScoutStrip'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'
import { formatThrownError } from '../i18n/utils'
import {
  dexHomeUrl,
  memeDexScreenerUrl,
  memeLaunchpadUrl,
  memeTerminalUrl,
} from '../lib/memeTerminalUrl'

type Tier = 'seed' | 'all' | 'fresh' | 'early' | 'watch'

type DexLane =
  | 'all'
  | 'seed'
  | 'raydium'
  | 'pumpfun'
  | 'bnb'
  | '4meme'
  | 'flap'
  | 'pancakeswap'
  | 'top-30'
  | 'gecko'
  | 'radar'
  | 'whispers'

const DEX_LANE_CHIPS: { key: DexLane; label: string }[] = [
  { key: 'all', label: 'Universe' },
  { key: 'seed', label: 'Seed' },
  { key: 'raydium', label: 'Raydium' },
  { key: 'pumpfun', label: 'Pump' },
  { key: 'bnb', label: 'BNB' },
  { key: '4meme', label: '4meme' },
  { key: 'flap', label: 'Flap' },
  { key: 'pancakeswap', label: 'PancakeSwap' },
  { key: 'top-30', label: 'Top-30' },
  { key: 'gecko', label: 'Gecko' },
  { key: 'radar', label: 'Binance radar' },
  { key: 'whispers', label: 'Whispers' },
]

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
  const [arena, setArena] = useState<DexArenaSnapshot | null>(null)
  const [sessionClock, setSessionClock] = useState<SessionClockSnapshot | null>(null)
  const [tier, setTier] = useState<Tier>('seed')
  const [dexLane, setDexLane] = useState<DexLane>('all')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const dexParam = dexLane === 'all' ? null : dexLane
      const [st, c, w, tr, te, ar, sc] = await Promise.all([
        fetchLaunchStatus(),
        fetchLaunchCandidates(tier, 80, dexParam),
        fetchLaunchWhispers(24),
        fetchLaunchTraders(30),
        fetchLaunchTraderEvents(24),
        fetchDexArena(),
        fetchSessionClock(),
      ])
      setStatus(st)
      setCandidates(c.candidates || [])
      setWhispers(w.whispers || [])
      setTraders(tr.traders || [])
      setTraderEvents(te.events || [])
      setArena(ar)
      setSessionClock(sc)
    } catch (err) {
      setError(formatThrownError(err, t('launch.loadError')))
    } finally {
      setLoading(false)
    }
  }, [t, tier, dexLane])

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
        {status?.last_warnings ? (
          <p className="pres-next-term-note">{t('launch.degradedWarnings', { msg: status.last_warnings })}</p>
        ) : null}
        <div className="telemetry-chips launch-source-chips" role="group" aria-label={t('launch.dexFilter')}>
          {DEX_LANE_CHIPS.map((chip) => {
            const label = chip.label
            const home =
              chip.key !== 'all' && chip.key !== 'seed' && chip.key !== 'top-30' && chip.key !== 'radar' && chip.key !== 'whispers' && chip.key !== 'gecko'
                ? dexHomeUrl(chip.key === 'bnb' ? 'pancakeswap' : chip.key, chip.key === 'bnb' ? 'bsc' : 'solana')
                : null
            return (
              <button
                key={chip.key}
                type="button"
                className={`pres-season-chip tap-target ${dexLane === chip.key ? 'season-best_six' : ''}`}
                onClick={() => setDexLane(chip.key)}
              >
                {label}
                {home ? (
                  <a
                    href={home}
                    target="_blank"
                    rel="noreferrer"
                    className="launch-dex-home-mini"
                    onClick={(e) => e.stopPropagation()}
                    title={t('launch.openDexHome')}
                  >
                    ↗
                  </a>
                ) : null}
              </button>
            )
          })}
        </div>
        {status?.last_error && <p className="pearl-agent-error">{status.last_error}</p>}
        <p className="pres-next-term-note">{t('launch.cexNote')}</p>
      </header>

      <LaunchScoutStrip />

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('launch.sessionClockTitle')}</h2>
          <span className="pearl-meta">
            {sessionClock?.now_session_label || sessionClock?.now_session || '—'}
            {sessionClock?.now_hour_utc != null ? ` · ${sessionClock.now_hour_utc}:00 UTC` : ''}
          </span>
        </div>
        {!sessionClock?.ok && sessionClock?.reason === 'disabled' ? (
          <p className="empty-state">{t('launch.sessionClockDisabled')}</p>
        ) : (
          <>
            <p className="pearl-lead">
              {t('launch.sessionClockLead', {
                session: sessionClock?.now_session_label || sessionClock?.now_session || '—',
                hot: sessionClock?.hot_lane || '—',
              })}
            </p>
            <div className="session-clock-bar" role="img" aria-label={t('launch.sessionClockHeatmap')}>
              {(sessionClock?.heatmap?.hours || Array.from({ length: 24 }, (_, h) => ({ hour_utc: h, activity: 0 }))).map(
                (cell) => {
                  const act = Number(cell.activity || 0)
                  const maxAct = Math.max(
                    1,
                    ...(sessionClock?.heatmap?.hours || []).map((x) => Number(x.activity || 0)),
                  )
                  const intensity = Math.min(1, act / maxAct)
                  const isNow = cell.hour_utc === sessionClock?.now_hour_utc
                  return (
                    <div
                      key={cell.hour_utc}
                      className={`session-clock-cell ${isNow ? 'now' : ''}`}
                      title={`${cell.hour_utc}:00 UTC · ${'session' in cell ? cell.session || '' : ''} · act ${act.toFixed(0)}`}
                      style={{ opacity: 0.35 + intensity * 0.65 }}
                    />
                  )
                },
              )}
            </div>
            <div className="telemetry-chips" style={{ marginTop: '0.5rem' }}>
              {(sessionClock?.macro_bias?.sessions || []).slice(0, 4).map((s) => (
                <span key={s.session} className="pres-season-chip">
                  {s.label || s.session}: {s.bias || '—'}
                  {s.avg_log_return != null ? ` · ln ${s.avg_log_return.toFixed(4)}` : ''}
                </span>
              ))}
            </div>
          </>
        )}
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('launch.dexArenaTitle')}</h2>
          <span className="pearl-meta">
            {t('launch.dexArenaMeta', {
              n: arena?.boards?.length ?? 0,
              w: arena?.whale_mints_tracked ?? 0,
            })}
          </span>
        </div>
        {!arena?.boards?.length ? (
          <p className="empty-state">{t('launch.dexArenaEmpty')}</p>
        ) : (
          <div className="launch-dex-arena-grid">
            {(arena.boards || []).map((board) => (
              <div key={board.dex_id} className="launch-dex-arena-card">
                <div className="launch-dex-arena-head">
                  <strong>{board.label || board.dex_id}</strong>
                  <span className="pearl-meta">{board.candidate_count}</span>
                  {board.home_url ? (
                    <a href={board.home_url} target="_blank" rel="noreferrer" className="link-btn">
                      {t('launch.openDexHome')}
                    </a>
                  ) : null}
                </div>
                {(board.best || []).length === 0 ? (
                  <p className="pres-next-term-note">{t('launch.dexArenaLaneEmpty')}</p>
                ) : (
                  <ul className="fomo-strip-feed">
                    {board.best.slice(0, 5).map((pick) => {
                      const href =
                        pick.url ||
                        memeTerminalUrl({
                          mint: pick.mint,
                          symbol: pick.symbol,
                          chain: pick.chain,
                          dexId: pick.dex_id,
                        })
                      return (
                        <li key={`${board.dex_id}-${pick.mint || pick.symbol}`} className="fomo-strip-item">
                          {pick.whale ? <span className="fomo-strip-buy">{t('launch.whaleBadge')}</span> : null}
                          {href ? (
                            <a href={href} target="_blank" rel="noreferrer">
                              <strong>{pick.symbol}</strong>
                            </a>
                          ) : (
                            <strong>{pick.symbol}</strong>
                          )}
                          <span className="fomo-strip-usd">{formatUsd(pick.market_cap)}</span>
                          <span className="fomo-strip-chain">+{Math.round(pick.whale_boost || 0)}</span>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('launch.tradersTitle')}</h2>
          <span className="pearl-meta">
            {t('launch.tradersMeta', { n: traders.length })}
            {status?.wallet_scout?.open_bags != null
              ? ` · ${t('launch.walletScoutMeta', {
                  bags: status.wallet_scout.open_bags ?? 0,
                  w: status.wallet_scout.wallets_scanned ?? 0,
                })}`
              : ''}
          </span>
        </div>
        {traders.length === 0 ? (
          <p className="empty-state">{t('launch.tradersEmpty')}</p>
        ) : (
          <ul className="fomo-strip-feed launch-whisper-feed launch-trader-feed">
            {traders.slice(0, 12).map((tr) => {
              const bags = (tr.bags || []).filter((b) => b.status !== 'closed').slice(0, 4)
              const sideLabel =
                tr.last_side === 'sell' ? t('launch.sell') : tr.last_side === 'buy' ? t('launch.buy') : null
              return (
                <li key={tr.wallet} className="fomo-strip-item launch-trader-row">
                  <div className="launch-trader-main">
                    <span className="fomo-strip-buy">#{tr.rank}</span>
                    <code className="fomo-event-mint">{shortMint(tr.wallet)}</code>
                    <span className="fomo-strip-usd">
                      {tr.buys ?? 0} buys
                      {(tr.sells ?? 0) > 0 ? ` · ${tr.sells} sells` : ''}
                    </span>
                    {sideLabel ? (
                      <span className={tr.last_side === 'sell' ? 'fomo-strip-sell' : 'fomo-strip-buy'}>
                        {sideLabel}
                      </span>
                    ) : null}
                    {(tr.open_bags ?? 0) > 0 ? (
                      <span className="fomo-strip-chain">
                        {t('launch.openBags')}: {tr.open_bags}
                      </span>
                    ) : null}
                    <span className="fomo-strip-chain">{tr.source || 'pump'}</span>
                  </div>
                  {bags.length > 0 ? (
                    <ul className="launch-bag-list">
                      {bags.map((bag) => {
                        const href =
                          memeTerminalUrl({
                            mint: bag.mint,
                            symbol: bag.symbol,
                            chain: bag.chain || 'solana',
                            url: bag.url,
                          }) ||
                          memeDexScreenerUrl({
                            mint: bag.mint,
                            symbol: bag.symbol,
                            chain: bag.chain || 'solana',
                          })
                        const dex = memeDexScreenerUrl({
                          mint: bag.mint,
                          symbol: bag.symbol,
                          chain: bag.chain || 'solana',
                        })
                        return (
                          <li key={`${tr.wallet}-${bag.mint}`} className="launch-bag-item">
                            <strong>{bag.symbol}</strong>
                            <span className="fomo-strip-buy">
                              {bag.side === 'long' ? t('launch.bagLong') : bag.side || '—'}
                            </span>
                            <span className="fomo-strip-usd">{formatUsd(bag.net_usd)}</span>
                            {href ? (
                              <a href={href} target="_blank" rel="noreferrer" className="link-btn">
                                {t('launch.axiomLink')}
                              </a>
                            ) : null}
                            {dex && dex !== href ? (
                              <a href={dex} target="_blank" rel="noreferrer" className="link-btn">
                                {t('launch.dexLink')}
                              </a>
                            ) : null}
                            <a
                              href={dexHomeUrl('pumpfun', 'solana')}
                              target="_blank"
                              rel="noreferrer"
                              className="link-btn"
                            >
                              {t('launch.openDexHome')}
                            </a>
                          </li>
                        )
                      })}
                    </ul>
                  ) : null}
                </li>
              )
            })}
          </ul>
        )}
        {traderEvents.length > 0 && (
          <>
            <h3 className="section-title" style={{ marginTop: '1rem' }}>
              {t('launch.traderEventsTitle')}
            </h3>
            <ul className="fomo-strip-feed">
              {traderEvents.slice(0, 10).map((ev) => {
                const href =
                  memeTerminalUrl({
                    mint: ev.mint,
                    symbol: ev.symbol,
                    chain: ev.chain || 'solana',
                  }) ||
                  memeDexScreenerUrl({
                    mint: ev.mint,
                    symbol: ev.symbol,
                    chain: ev.chain || 'solana',
                  })
                const dex = memeDexScreenerUrl({
                  mint: ev.mint,
                  symbol: ev.symbol,
                  chain: ev.chain || 'solana',
                })
                const isSell = String(ev.action || '').toLowerCase() === 'sell'
                return (
                  <li key={ev.event_id} className="fomo-strip-item">
                    <span className={isSell ? 'fomo-strip-sell' : 'fomo-strip-buy'}>
                      {isSell ? t('launch.sell') : t('launch.buy')}
                    </span>
                    <strong>{ev.symbol}</strong>
                    <span className="fomo-strip-usd">{formatUsd(ev.usd_amount)}</span>
                    <code className="fomo-event-mint">{shortMint(ev.wallet)}</code>
                    {href ? (
                      <a href={href} target="_blank" rel="noreferrer" className="link-btn">
                        {t('launch.axiomLink')}
                      </a>
                    ) : null}
                    {dex && dex !== href ? (
                      <a href={dex} target="_blank" rel="noreferrer" className="link-btn">
                        {t('launch.dexLink')}
                      </a>
                    ) : null}
                  </li>
                )
              })}
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
                            {(() => {
                              const home =
                                c.dex_home_url ||
                                dexHomeUrl(c.dex_id || c.source, c.chain)
                              return home ? (
                                <a href={home} target="_blank" rel="noreferrer" className="link-btn">
                                  {t('launch.openDexHome')}
                                </a>
                              ) : null
                            })()}
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
