import { useCallback, useEffect, useState } from 'react'
import { fetchSocialStatus, type SocialDeskStatus } from '../api'
import { useLocale } from '../context/LocaleContext'

export function SocialDeskPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { t } = useLocale()
  const [status, setStatus] = useState<SocialDeskStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setStatus(await fetchSocialStatus())
    } catch {
      setStatus(null)
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
          ? ` · auto ≤ ${status.auto_max_per_day ?? 2}/24h · próg ${status.auto_min_score ?? 70}`
          : ' · auto wyłączone'}
      </p>
      <p className="empty-state social-desk-empty">{t('macro.social.empty')}</p>
    </section>
  )
}
