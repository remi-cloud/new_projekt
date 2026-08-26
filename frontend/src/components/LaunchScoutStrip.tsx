import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchLaunchCandidates,
  fetchLaunchTraders,
  fetchLaunchWhispers,
  type LaunchCandidate,
} from '../api'
import { memeDexScreenerUrl, memeTerminalUrl } from '../lib/memeTerminalUrl'
import { CoinAvatar } from './CoinAvatar'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'

function formatUsd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  if (Math.abs(n) >= 1000) return `$${Math.round(n).toLocaleString()}`
  return `$${n.toFixed(0)}`
}

function candidateTerminal(c: LaunchCandidate): string | null {
  return (
    memeTerminalUrl({
      mint: c.mint,
      symbol: c.symbol,
      chain: c.chain,
      pairAddress: c.pair_address,
      url: c.url,
      source: c.source,
      dexId: c.dex_id,
    }) ||
    c.url ||
    null
  )
}

export function LaunchScoutStrip() {
  const { t } = useLocale()
  const [rows, setRows] = useState<LaunchCandidate[]>([])
  const [whisperN, setWhisperN] = useState(0)
  const [traderN, setTraderN] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    Promise.all([
      fetchLaunchCandidates('seed', 12),
      fetchLaunchWhispers(8),
      fetchLaunchTraders(30),
    ])
      .then(([d, w, tr]) => {
        const cands = d.candidates || []
        if (cands.length === 0) {
          return fetchLaunchCandidates('fresh', 12).then((f) => {
            setRows(f.candidates || [])
            setWhisperN((w.whispers || []).length)
            setTraderN((tr.traders || []).length)
            setError(null)
          })
        }
        setRows(cands)
        setWhisperN((w.whispers || []).length)
        setTraderN((tr.traders || []).length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'launch error'))
  }, [])

  useEffect(() => {
    load()
    const id = window.setInterval(load, 60_000)
    return () => window.clearInterval(id)
  }, [load])

  useLiveFeed((ev) => {
    if (ev.type === 'launch_scout_tick') load()
  })

  return (
    <section className="dashboard-section fomo-ghost-strip launch-scout-strip">
      <div className="section-header">
        <h2 className="section-title">{t('launch.stripTitle')}</h2>
        <div className="telemetry-chips">
          <span className="pres-season-chip season-best_six">{t('launch.flagshipBadge')}</span>
          <span className="pres-season-chip season-best_six">{t('launch.stripLive')}</span>
          {traderN > 0 && (
            <span className="pres-season-chip">{t('launch.tradersMeta', { n: traderN })}</span>
          )}
          {whisperN > 0 && (
            <span className="pres-season-chip">{t('launch.whispersMeta', { n: whisperN })}</span>
          )}
          <Link to="/launch" className="link-btn tap-target card-nav-link">
            {t('launch.openDesk')}
          </Link>
        </div>
      </div>
      <p className="page-lead">{t('launch.stripLead')}</p>
      {error && <p className="empty-state">{error}</p>}
      {!error && rows.length === 0 && <p className="empty-state">{t('launch.stripEmpty')}</p>}
      {rows.length > 0 && (
        <ul className="fomo-strip-feed">
          {rows.slice(0, 8).map((c) => {
            const term = candidateTerminal(c)
            const dex = memeDexScreenerUrl({
              mint: c.mint,
              symbol: c.symbol,
              chain: c.chain,
              pairAddress: c.pair_address,
            })
            return (
              <li key={c.candidate_id} className="fomo-strip-item">
                <CoinAvatar symbol={c.symbol} name={c.name} imageUrl={c.image_url} size={22} />
                <span className="fomo-strip-buy">
                  {c.tier === 'seed' ? t('launch.tierSeed') : t('launch.tierFresh')}
                </span>
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
                <span className="fomo-strip-usd">{formatUsd(c.market_cap)}</span>
                <span className="fomo-strip-chain">{c.chain}</span>
                <span className="fomo-strip-token">{c.dex_id || '—'}</span>
                {dex && (
                  <a href={dex} target="_blank" rel="noreferrer" className="link-btn">
                    {t('launch.openDex')}
                  </a>
                )}
                {(c.tags || []).includes('pump_trader') && (
                  <span className="fomo-strip-buy">{t('launch.tradersChip')}</span>
                )}
                {(c.tags || []).includes('4meme') && <span className="fomo-strip-buy">4meme</span>}
                {(c.tags || []).includes('flap') && <span className="fomo-strip-buy">Flap</span>}
                {(c.tags || []).includes('pancake') && <span className="fomo-strip-buy">PCS</span>}
                {(c.tags || []).includes('elon_whisper') && (
                  <span className="fomo-strip-buy">{t('launch.authorElon')}</span>
                )}
                {(c.tags || []).includes('cz_whisper') && (
                  <span className="fomo-strip-buy">{t('launch.authorCz')}</span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
