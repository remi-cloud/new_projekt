import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchEmbedCycle, type EmbedCyclePayload } from '../api'
import { ErrorState } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { formatThrownError, resolveApiMessage } from '../i18n/utils'

export function EmbedPage() {
  const { t, dateLocale } = useLocale()
  const { phase, signal } = useDomainLabels()
  const [data, setData] = useState<EmbedCyclePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchEmbedCycle())
    } catch (err) {
      setData(null)
      setError(formatThrownError(err, resolveApiMessage('embedFailed')))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const snippet = `<iframe src="${window.location.origin}/embed/widget" width="360" height="220" style="border:0;border-radius:12px" title="Cyclical Academy embed"></iframe>`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="growth-embed institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('growth.embedEyebrow')}</span>
        <h2 className="page-headline">{t('growth.embedHeadline')}</h2>
        <p className="page-lead">{t('growth.embedLead')}</p>
      </header>

      {error && <ErrorState message={error} onRetry={() => void load()} />}

      <div className="growth-embed-preview-wrap">
        <div className="cycle-embed-card">
          {loading && !data ? (
            <p>{t('growth.scanWait')}</p>
          ) : data ? (
            <>
              <div className="cycle-embed-brand">{data.brand}</div>
              <div className="cycle-embed-phase">
                {phase(data.phase)} · {signal[data.signal as keyof typeof signal] ?? data.signal}
              </div>
              <div className="cycle-embed-stats">
                <span>{t('growth.embedDay', { n: data.days_since_ath })}</span>
                <span>${data.current_price.toLocaleString(dateLocale)}</span>
                <span>{data.progress_pct.toFixed(0)}%</span>
              </div>
              <p>{data.rationale}</p>
              <div className="cycle-embed-foot">
                <Link to="/live">{t('growth.embedLiveLink')}</Link>
                <span>{data.disclaimer}</span>
              </div>
            </>
          ) : !error ? (
            <p>{t('growth.scanWait')}</p>
          ) : null}
        </div>
      </div>

      <section className="growth-section">
        <h3>{t('growth.embedCode')}</h3>
        <pre className="growth-code">{snippet}</pre>
        <button type="button" className="btn tap-target" onClick={() => void copy()}>
          {copied ? t('growth.copied') : t('growth.copyEmbed')}
        </button>
        <p className="growth-body" style={{ marginTop: 12 }}>
          JSON:{' '}
          <a href="/api/embed/cycle">/api/embed/cycle</a>
          {' · '}
          {t('growth.embedJsonDocs', { page: t('nav.business') })}
        </p>
      </section>

      <p className="growth-disclaimer">{t('growth.compliance')}</p>
    </div>
  )
}
