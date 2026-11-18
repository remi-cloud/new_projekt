import { useCallback, useEffect, useState } from 'react'
import { fetchSocialPublished, fetchSocialStatus, type SocialDeskStatus } from '../api'
import { useLocale } from '../context/LocaleContext'

type PublishedPost = {
  id?: number
  body: string
  published_at?: string | null
}

export function SocialDeskPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { t } = useLocale()
  const [status, setStatus] = useState<SocialDeskStatus | null>(null)
  const [published, setPublished] = useState<PublishedPost[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [desk, sent] = await Promise.all([
        fetchSocialStatus(),
        fetchSocialPublished(12),
      ])
      setStatus(desk)
      setPublished(sent.posts ?? [])
    } catch {
      setStatus(null)
      setPublished([])
    } finally {
      setLoading(false)
    }
  }, [])

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
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
