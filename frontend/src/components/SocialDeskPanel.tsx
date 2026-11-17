import { useCallback, useEffect, useState } from 'react'
import {
  fetchSocialDecisions,
  fetchSocialPosts,
  publishSocialPost,
  type SocialDecision,
  type SocialDeskStatus,
  type SocialPost,
} from '../api'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'

export function SocialDeskPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { t } = useLocale()
  const [posts, setPosts] = useState<SocialPost[]>([])
  const [decisions, setDecisions] = useState<SocialDecision[]>([])
  const [status, setStatus] = useState<SocialDeskStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [publishingId, setPublishingId] = useState<number | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [data, log] = await Promise.all([fetchSocialPosts(16), fetchSocialDecisions(20)])
      setPosts(data.posts)
      setStatus(data.status)
      setDecisions(log.decisions)
    } catch {
      setPosts([])
      setDecisions([])
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    void load()
  }, [load, refreshKey])

  const handlePublish = async (id: number) => {
    if (!confirm(t('macro.social.confirmPublish'))) return
    setPublishingId(id)
    setMsg(null)
    try {
      await publishSocialPost(id)
      setMsg(t('macro.social.published'))
      await load()
    } catch (e) {
      setMsg(formatThrownError(e, t('macro.social.publishFailed')))
    } finally {
      setPublishingId(null)
    }
  }

  if (loading && !status) {
    return <p className="social-desk-loading">{t('macro.social.loading')}</p>
  }
  if (!status?.enabled) return null

  const platforms = status.platforms?.length ? status.platforms : ['x']
  const visible = posts.filter((post) => platforms.includes(post.platform))
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
          ? ` · auto ≤ ${status.auto_max_per_hour ?? 2}/h · próg ${status.auto_min_score ?? 70}`
          : ' · auto wyłączone'}
      </p>
      {msg && <p className="social-desk-msg">{msg}</p>}
      {visible.length === 0 ? (
        <p className="empty-state social-desk-empty">{t('macro.social.empty')}</p>
      ) : (
        <ul className="social-desk-list">
          {visible.map((p) => (
            <li key={p.id} className="social-desk-item">
              <div className="social-desk-item-top">
                <strong className="social-desk-platform">{p.platform.toUpperCase()}</strong>
                <span className={`social-desk-status status-${p.status}`}>
                  {p.status === 'ready' ? t('macro.social.modeManual') : p.status}
                </span>
              </div>
              <p className="social-desk-body">{p.body}</p>
              {p.error && <p className="social-desk-error">{p.error}</p>}
              {p.status !== 'posted' && (
                <button
                  type="button"
                  className="btn btn-ghost tap-target social-desk-publish"
                  disabled={publishingId === p.id}
                  onClick={() => void handlePublish(p.id)}
                >
                  {publishingId === p.id ? '…' : t('macro.social.publish')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="social-desk-log">
        <h4>{t('macro.social.decisionsTitle')}</h4>
        {decisions.length === 0 ? (
          <p className="social-desk-empty">{t('macro.social.decisionsEmpty')}</p>
        ) : (
          <ul className="social-desk-list">
            {decisions.map((row) => (
              <li key={row.id} className="social-desk-item">
                <div className="social-desk-item-top">
                  <strong>{row.action}</strong>
                  <span>{row.source || '—'}</span>
                </div>
                <p className="social-desk-body">
                  {row.title ? `${row.title} — ` : ''}
                  {row.reason}
                  {row.score ? ` · ${row.score}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
