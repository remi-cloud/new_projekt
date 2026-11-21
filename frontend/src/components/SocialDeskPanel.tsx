import { useCallback, useEffect, useState } from 'react'
import { fetchSocialDecisions, fetchSocialPublished, fetchSocialStatus, type SocialDeskStatus } from '../api'
import { useLocale } from '../context/LocaleContext'
import { useDeskSession } from '../hooks/useDeskSession'

type PublishedPost = {
  id?: number
  body: string
  published_at?: string | null
  x_url?: string | null
  source_name?: string
}

type DecisionRow = {
  id?: number
  title?: string
  action?: string
  reason?: string
  score?: number
}

export function SocialDeskPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { t } = useLocale()
  const authed = useDeskSession()
  const [status, setStatus] = useState<SocialDeskStatus | null>(null)
  const [published, setPublished] = useState<PublishedPost[]>([])
  const [decisions, setDecisions] = useState<DecisionRow[] | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      // The decision log is desk-only; guests skip it so no 401/403 is logged.
      const [desk, sent, log] = await Promise.all([
        fetchSocialStatus(),
        fetchSocialPublished(12),
        authed ? fetchSocialDecisions(12) : Promise.resolve(null),
      ])
      setStatus(desk)
      setPublished(sent.posts ?? [])
      setDecisions(log ? (log.decisions ?? []) : null)
    } catch {
      setStatus(null)
      setPublished([])
      setDecisions(null)
    } finally {
      setLoading(false)
    }
  }, [authed])

  useEffect(() => {
    setLoading(true)
    void load()
  }, [load, refreshKey])

  if (loading && !status) {
    return <p className="social-desk-loading">{t('macro.social.loading')}</p>
  }
  if (!status?.enabled) return null

  const modeLabel = status.dry_run
    ? t('macro.social.modeDryRun')
    : status.auto_post
      ? t('macro.social.modeAuto')
      : t('macro.social.modeManual')

  return (
    <section className="social-desk" aria-label={t('macro.social.title')}>
      <div className="social-desk-head">
        <h3 className="social-desk-title">{t('macro.social.title')}</h3>
        <span className={`social-desk-badge ${status.dry_run ? 'dry' : 'live'}`}>{modeLabel}</span>
      </div>
      <p className="social-desk-meta">
        X: {status.x_configured ? t('macro.social.ready') : t('macro.social.noTokens')} · LinkedIn:{' '}
        {status.linkedin_configured ? t('macro.social.ready') : t('macro.social.noTokens')}
        {status.auto_post
          ? status.domain_ready
            ? ` · auto ≤ ${status.auto_max_per_hour ?? 2}/h · ≤ ${status.auto_max_per_day ?? 2}/24h · próg ${status.auto_min_score ?? 70}`
            : ' · auto włączone · czeka na domenę'
          : ' · auto wyłączone'}
      </p>
      <div className="social-desk-log">
        <h4>{t('macro.social.monitor')}</h4>
        {published.length === 0 ? (
          <p className="social-desk-empty">{t('macro.social.publishedEmpty')}</p>
        ) : (
          <ul className="social-desk-list">
            {published.map((row) => (
              <li key={row.id ?? row.published_at ?? row.body} className="social-desk-item">
                <p className="social-desk-body">{row.body}</p>
                {row.x_url ? (
                  <a href={row.x_url} rel="noreferrer">
                    {row.source_name || 'X'}
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {decisions ? (
          <>
            <h4>{t('macro.social.decisionsTitle')}</h4>
            {decisions.length === 0 ? (
              <p className="social-desk-empty">{t('macro.social.decisionsEmpty')}</p>
            ) : (
              <ul className="social-desk-list">
                {decisions.map((row) => (
                  <li key={row.id ?? `${row.action}-${row.title}`} className="social-desk-item">
                    <p className="social-desk-body">
                      {row.action}: {row.title || row.reason}
                      {row.reason ? ` — ${row.reason}` : ''}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : null}
      </div>
    </section>
  )
}
