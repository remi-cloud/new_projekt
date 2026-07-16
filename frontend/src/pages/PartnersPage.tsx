import { Link } from 'react-router-dom'
import { NewsletterSignup } from '../components/NewsletterSignup'
import { useLocale } from '../context/LocaleContext'

export function PartnersPage() {
  const { t } = useLocale()

  return (
    <div className="growth-partners institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('growth.partnersEyebrow')}</span>
        <h2 className="page-headline">{t('growth.partnersHeadline')}</h2>
        <p className="page-lead">{t('growth.partnersLead')}</p>
      </header>

      <div className="growth-partner-grid">
        <section className="growth-card">
          <h3>{t('growth.wlTitle')}</h3>
          <p>{t('growth.wlBody')}</p>
          <ul>
            <li>{t('growth.wl1')}</li>
            <li>{t('growth.wl2')}</li>
            <li>{t('growth.wl3')}</li>
          </ul>
        </section>
        <section className="growth-card">
          <h3>{t('growth.mediaTitle')}</h3>
          <p>{t('growth.mediaBody')}</p>
          <ul>
            <li>{t('growth.media1')}</li>
            <li>{t('growth.media2')}</li>
            <li>{t('growth.media3')}</li>
          </ul>
        </section>
        <section className="growth-card">
          <h3>{t('growth.eduTitle')}</h3>
          <p>{t('growth.eduBody')}</p>
          <ul>
            <li>{t('growth.edu1')}</li>
            <li>{t('growth.edu2')}</li>
            <li>{t('growth.edu3')}</li>
          </ul>
        </section>
      </div>

      <div className="growth-live-actions">
        <Link className="btn tap-target" to="/biznes">
          {t('growth.ctaBiz')}
        </Link>
        <Link className="btn btn-ghost tap-target" to="/embed">
          {t('growth.ctaEmbed')}
        </Link>
        <a className="btn btn-ghost tap-target" href="/api/embed/cycle" target="_blank" rel="noreferrer">
          {t('growth.apiSandbox')}
        </a>
      </div>

      <NewsletterSignup source="partners" />
      <p className="growth-disclaimer">{t('growth.compliance')}</p>
    </div>
  )
}
