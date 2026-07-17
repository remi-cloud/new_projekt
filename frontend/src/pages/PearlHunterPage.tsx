import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchPearlFinds, fetchPearlStatus, runPearlHunt } from '../api'
import { BrokerPurchaseHint } from '../components/BrokerPurchaseHint'
import { InstrumentShareMenu } from '../components/InstrumentShareMenu'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { formatThrownError } from '../i18n/utils'
import type { PearlFind, PearlHunterStatus } from '../types'
import { formatPrice } from '../utils/format'

export function PearlHunterPage() {
  const navigate = useNavigate()
  const { t, dateLocale } = useLocale()
  const { signal } = useDomainLabels()
  const [status, setStatus] = useState<PearlHunterStatus | null>(null)
  const [finds, setFinds] = useState<PearlFind[]>([])
  const [agentFilter, setAgentFilter] = useState<'all' | 'pearl_equity' | 'pearl_crypto'>('all')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [st, list] = await Promise.all([
        fetchPearlStatus(),
        fetchPearlFinds(agentFilter === 'all' ? undefined : agentFilter),
      ])
      setStatus(st)
      setFinds(list)
    } catch (err) {
      setError(formatThrownError(err, t('pearl.loadError')))
    } finally {
      setLoading(false)
    }
  }, [agentFilter, t])

  useEffect(() => {
    void load()
  }, [load])

  const onRun = async () => {
    setRunning(true)
    try {
      await runPearlHunt('both')
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('pearl.runError')))
    } finally {
      setRunning(false)
    }
  }

  const filtered = useMemo(() => {
    if (agentFilter === 'all') return finds
    return finds.filter((f) => f.agent_id === agentFilter)
  }, [finds, agentFilter])

  if (loading && !finds.length) return <Loading message={t('pearl.loading')} />
  if (error && !finds.length) return <ErrorState message={error} onRetry={() => void load()} />

  return (
    <div className="pearl-page">
      <header className="pearl-header">
        <span className="page-eyebrow">{t('pearl.eyebrow')}</span>
        <h1 className="page-title">{t('pearl.title')}</h1>
        <p className="pearl-lead">{t('pearl.lead')}</p>
        <div className="pearl-status-bar">
          <span className={`pearl-live-pill ${status?.enabled ? 'on' : ''}`}>
            {status?.enabled ? t('pearl.scanning24') : t('pearl.disabled')}
          </span>
          <span className="pearl-meta">
            {t('pearl.findsCount', { n: status?.finds_count ?? filtered.length })}
            {status?.last_run_at
              ? ` · ${t('pearl.lastRun', { date: new Date(status.last_run_at).toLocaleString(dateLocale) })}`
              : ''}
          </span>
          <button type="button" className="btn btn-primary tap-target" onClick={() => void onRun()} disabled={running}>
            {running ? t('pearl.running') : t('pearl.runNow')}
          </button>
        </div>
        {status?.agents && (
          <div className="pearl-agents">
            {status.agents.map((a) => (
              <div key={a.id} className="pearl-agent-card">
                <strong>{a.id === 'pearl_equity' ? t('pearl.agentEquity') : t('pearl.agentCrypto')}</strong>
                <span>
                  {t('pearl.agentLast', {
                    n: a.last_count ?? 0,
                    date: a.last_run_at ? new Date(a.last_run_at).toLocaleString(dateLocale) : '—',
                  })}
                </span>
                {a.last_error ? <em className="pearl-agent-error">{a.last_error}</em> : null}
              </div>
            ))}
          </div>
        )}
      </header>

      <div className="filter-section">
        <div className="filter-label">{t('pearl.filterAgent')}</div>
        <div className="filter-chips">
          {(
            [
              ['all', t('pearl.filterAll')],
              ['pearl_equity', t('pearl.agentEquity')],
              ['pearl_crypto', t('pearl.agentCrypto')],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`filter-chip ${agentFilter === value ? 'active' : ''}`}
              onClick={() => setAgentFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="empty-state">{t('pearl.empty')}</p>
      ) : (
        <div className="pearl-grid">
          {filtered.map((find) => (
            <article
              key={`${find.agent_id}-${find.symbol}`}
              className="pearl-card pearl-card-clickable"
              role="link"
              tabIndex={0}
              onClick={() => navigate(`/instrument/${encodeURIComponent(find.symbol)}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigate(`/instrument/${encodeURIComponent(find.symbol)}`)
                }
              }}
            >
              <div className="pearl-card-head">
                <div>
                  <h3>{find.name}</h3>
                  <div className="pearl-symbol">{find.symbol}</div>
                </div>
                <div className="pearl-card-head-actions" onClick={(e) => e.stopPropagation()}>
                  <InstrumentShareMenu
                    symbol={find.symbol}
                    name={find.name}
                    kind="pearl"
                    signal={signal[find.action] ?? find.action}
                    compact
                  />
                  <span className={`signal-tag signal-${find.action}`}>
                    {signal[find.action] ?? find.action}
                  </span>
                </div>
              </div>
              <div className="pearl-price">
                ${formatPrice(find.price, find.asset_class)}
                {find.change_pct_24h != null && (
                  <em className={find.change_pct_24h >= 0 ? 'pos' : 'neg'}>
                    {find.change_pct_24h >= 0 ? '+' : ''}
                    {find.change_pct_24h.toFixed(1)}%
                  </em>
                )}
              </div>
              <div className="confidence-bar">
                <div className="confidence-track">
                  <div className="confidence-fill" style={{ width: `${find.confidence}%` }} />
                </div>
                <span className="confidence-pct">{Math.round(find.score)} pts</span>
              </div>
              <p className="pearl-rationale">{find.rationale}</p>
              <div className="pearl-card-meta">
                <span>{find.agent_id === 'pearl_equity' ? t('pearl.agentEquity') : t('pearl.agentCrypto')}</span>
                <span>{new Date(find.found_at).toLocaleString(dateLocale)}</span>
              </div>
              <BrokerPurchaseHint info={find.broker_info} compact />
              <button
                type="button"
                className="btn btn-secondary tap-target pearl-open-chart"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/instrument/${encodeURIComponent(find.symbol)}`)
                }}
              >
                {t('pearl.openChart')}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
