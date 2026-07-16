import { FormEvent, useState } from 'react'
import { subscribeNewsletter } from '../api'
import { useLocale } from '../context/LocaleContext'

type Props = {
  source?: string
  compact?: boolean
}

export function NewsletterSignup({ source = 'web', compact = false }: Props) {
  const { t, locale } = useLocale()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'err'>('idle')

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setStatus('loading')
    try {
      await subscribeNewsletter(email, locale, source)
      setStatus('ok')
      setEmail('')
    } catch {
      setStatus('err')
    }
  }

  return (
    <form className={`growth-newsletter ${compact ? 'compact' : ''}`} onSubmit={onSubmit}>
      {!compact && (
        <>
          <h3>{t('growth.newsletterTitle')}</h3>
          <p>{t('growth.newsletterLead')}</p>
        </>
      )}
      <div className="growth-newsletter-row">
        <input
          type="email"
          required
          placeholder={t('growth.newsletterEmail')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          aria-label={t('growth.newsletterEmail')}
        />
        <button type="submit" className="btn tap-target" disabled={status === 'loading'} data-i18n-cta="growth.newsletterCta">
          {status === 'loading' ? '…' : t('growth.newsletterCta')}
        </button>
      </div>
      {status === 'ok' && <p className="growth-ok">{t('growth.newsletterOk')}</p>}
      {status === 'err' && <p className="growth-err">{t('growth.newsletterErr')}</p>}
    </form>
  )
}
