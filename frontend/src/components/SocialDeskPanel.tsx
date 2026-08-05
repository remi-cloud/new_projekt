import { useCallback, useEffect, useState } from 'react'
import {
  fetchSocialPosts,
  publishSocialPost,
  type SocialDeskStatus,
  type SocialPost,
} from '../api'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'

export function SocialDeskPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { t } = useLocale()
  const [posts, setPosts] = useState<SocialPost[]>([])
  const [status, setStatus] = useState<SocialDeskStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [publishingId, setPublishingId] = useState<number | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await fetchSocialPosts(16)
      setPosts(data.posts)
      setStatus(data.status)
    } catch {
      setPosts([])
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
      </p>
      {msg && <p className="social-desk-msg">{msg}</p>}
      {posts.length === 0 ? (
        <p className="empty-state social-desk-empty">{t('macro.social.empty')}</p>
      ) : (
        <ul className="social-desk-list">
          {posts.map((p) => (
            <li key={p.id} className="social-desk-item">
              <div className="social-desk-item-top">
                <strong className="social-desk-platform">{p.platform.toUpperCase()}</strong>
                <span className={`social-desk-status status-${p.status}`}>{p.status}</span>
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
    </section>
  )
}
