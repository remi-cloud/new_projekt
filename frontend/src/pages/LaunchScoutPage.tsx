import { useEffect, useState } from 'react'
import { fetchLaunchCandidates, fetchLaunchStatus, type LaunchCandidate, type LaunchStatus } from '../api'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { formatPrice } from '../utils/format'

const TIERS = ['all', 'seed', 'fresh', 'early', 'watch'] as const

export function LaunchScoutPage() {
  const { t } = useLocale()
  const [tier, setTier] = useState<(typeof TIERS)[number]>('seed')
  const [status, setStatus] = useState<LaunchStatus | null>(null)
  const [rows, setRows] = useState<LaunchCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    ;(async () => {
      try {
        const [nextStatus, nextRows] = await Promise.all([
          fetchLaunchStatus(),
          fetchLaunchCandidates(tier),
        ])
        if (cancelled) return
        setStatus(nextStatus)
        setRows(nextRows.candidates ?? [])
      } catch {
        if (!cancelled) setError(t('launchPage.error'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tier, t, reloadKey])

  const retry = () => setReloadKey((value) => value + 1)

  if (loading && !status) return <Loading message={t('launchPage.loading')} />
  if (error && !status) return <ErrorState message={error} onRetry={retry} />

  const quiet = !status?.enabled || Boolean(status?.last_error)

  return (
    <div className="page launch-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('launchPage.eyebrow')}</span>
        <h2 className="page-headline">{t('launchPage.title')}</h2>
        <p className="page-lead">{t('launchPage.lead')}</p>
      </header>
      {quiet && <p className="desk-source-down" role="status">{t('launchPage.sourceDown')}</p>}
      {(status?.blocked_sources?.length ? status.blocked_sources : [{ id: 'sources', detail: t('launchPage.blockedSources') }]).map((source) => (
        <p className="desk-source-down" role="status" key={source.id}>
          {source.id === 'sources' ? source.detail : `${source.id}: ${source.detail || source.status || t('launchPage.blockedSources')}`}
        </p>
      ))}
      <div className="filter-chips" role="tablist">
        {TIERS.map((id) => (
          <button
            key={id}
            type="button"
            className={`chip${tier === id ? ' active' : ''}`}
            onClick={() => setTier(id)}
          >
            {t(`launchPage.${id}`)}
            {status?.counts?.[id] != null ? ` ${status.counts[id]}` : ''}
          </button>
        ))}
      </div>
      {rows.length === 0 ? (
        <p className="empty">{t('launchPage.empty')}</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('launchPage.colSymbol')}</th>
                <th>{t('launchPage.colTier')}</th>
                <th>{t('launchPage.colChain')}</th>
                <th>{t('launchPage.colMc')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 40).map((row) => (
                <tr key={`${row.chain ?? ''}-${row.symbol}-${row.mint ?? row.pair ?? ''}`}>
                  <td>{row.symbol}</td>
                  <td>{row.tier ?? '—'}</td>
                  <td>{row.chain ?? '—'}</td>
                  <td>{row.market_cap != null ? formatPrice(Number(row.market_cap)) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
