import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchGrowthPackages,
  submitBusinessLead,
  type GrowthPackage,
} from '../api'
import { NewsletterSignup } from '../components/NewsletterSignup'
import { ErrorState } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'

export function BusinessPage() {
  const { t, locale } = useLocale()
  const [packages, setPackages] = useState<GrowthPackage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pkg, setPkg] = useState('api')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'err'>('idle')

  useEffect(() => {
    void (async () => {
      try {
        setPackages(await fetchGrowthPackages())
      } catch {
        setError(t('growth.errors.packages'))
      }
    })()
  }, [t])

  useEffect(() => {
    if (window.location.hash === '#kontakt') {
      window.requestAnimationFrame(() => {
        document.getElementById('kontakt')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    }
  }, [])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setStatus('loading')
    try {
      await submitBusinessLead({ name, email, company, package: pkg, message, locale })
      setStatus('ok')
      setName('')
      setEmail('')
      setCompany('')
      setMessage('')
    } catch {
      setStatus('err')
    }
  }

  if (error && !packages.length) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  return (
    <div className="growth-biz institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('growth.bizEyebrow')}</span>
        <h2 className="page-headline">{t('growth.bizHeadline')}</h2>
        <p className="page-lead">{t('growth.bizLead')}</p>
      </header>

      <div className="growth-pkg-grid">
        {packages.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`growth-pkg ${pkg === p.id ? 'active' : ''}`}
            onClick={() => setPkg(p.id)}
          >
            <h3>{p.name}</h3>
            <p className="growth-price">{p.price}</p>
            <ul>
              {p.bullets.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </button>
        ))}
      </div>

      <section className="growth-section growth-channels">
        <h3>{t('growth.channelsTitle')}</h3>
        <div className="growth-channel-row">
          <a href="#kontakt" className="growth-channel">
            Telegram
          </a>
          <a href="#kontakt" className="growth-channel">
            Discord
          </a>
          <Link to="/embed" className="growth-channel">
            Embed / API
          </Link>
          <Link to="/partnerzy" className="growth-channel">
            {t('growth.partnersLink')}
          </Link>
        </div>
        <p className="growth-body" style={{ marginTop: 10 }}>
          {t('growth.channelsHint')}
        </p>
      </section>

      <section id="kontakt" className="growth-section">
        <h3>{t('growth.contactTitle')}</h3>
        <p className="growth-body">{t('growth.contactLead')}</p>
        <form className="growth-contact" onSubmit={onSubmit}>
          <label>
            {t('growth.contactName')}
            <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
          </label>
          <label>
            {t('growth.contactEmail')}
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            {t('growth.contactCompany')}
            <input value={company} onChange={(e) => setCompany(e.target.value)} />
          </label>
          <label>
            {t('growth.contactPackage')}
            <select value={pkg} onChange={(e) => setPkg(e.target.value)}>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="full">
            {t('growth.contactMessage')}
            <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)} />
          </label>
          <button type="submit" className="btn tap-target" disabled={status === 'loading'}>
            {status === 'loading' ? '…' : t('growth.contactCta')}
          </button>
          {status === 'ok' && <p className="growth-ok full">{t('growth.contactOk')}</p>}
          {status === 'err' && <p className="growth-err full">{t('growth.contactErr')}</p>}
        </form>
      </section>

      <NewsletterSignup source="biznes" />
      <p className="growth-disclaimer">{t('growth.compliance')}</p>
    </div>
  )
}
