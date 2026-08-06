import { Link } from 'react-router-dom'
import { KarDigitalLogo } from '../components/KarDigitalLogo'
import { useLocale } from '../context/LocaleContext'
import { translations } from '../i18n'
import {
  ABOUT_METHOD_SLUGS,
  ABOUT_NOT_SLUGS,
  ABOUT_PILLAR_SLUGS,
  aboutTopicPath,
} from '../i18n/aboutTopics'

export function AboutPage() {
  const { t, tArray, locale } = useLocale()
  const pillars = translations[locale].about.pillars
  const methodSteps = tArray('about.methodSteps')
  const notUs = tArray('about.notUs')
  const chips = tArray('about.chips')
  const learnMore = translations[locale].aboutDetail.learnMore

  return (
    <div className="about-page institutional-page">
      <header className="page-intro about-hero">
        <div className="about-hero-brand">
          <KarDigitalLogo size={72} variant="hero" />
        </div>
        <span className="page-eyebrow">{t('about.eyebrow')}</span>
        <h2 className="page-headline">{t('about.title')}</h2>
        <p className="about-principle">{t('about.principle')}</p>
        <p className="about-principle-note">{t('about.principleNote')}</p>
        <p className="page-lead about-lead">{t('about.lead')}</p>
      </header>

      <section className="about-manifesto">
        <blockquote className="about-quote">{t('about.quote')}</blockquote>
      </section>

      <section className="about-section">
        <div className="about-section-head">
          <h3 className="about-section-title">{t('about.whoTitle')}</h3>
          <p className="about-section-desc">{t('about.whoDesc')}</p>
        </div>
        <div className="about-pillars">
          {pillars.map((p, i) => {
            const slug = ABOUT_PILLAR_SLUGS[i]
            return (
              <Link key={slug} to={aboutTopicPath(slug)} className="about-pillar about-pillar-link tap-target">
                <h4>{p.title}</h4>
                <p>{p.body}</p>
                <span className="about-pillar-cta">{learnMore}</span>
              </Link>
            )
          })}
        </div>
      </section>

      <section className="about-section about-contrast">
        <div className="about-section-head">
          <h3 className="about-section-title">{t('about.notTitle')}</h3>
          <p className="about-section-desc">{t('about.notDesc')}</p>
        </div>
        <ul className="about-not-list">
          {notUs.map((line, i) => {
            const slug = ABOUT_NOT_SLUGS[i]
            return (
              <li key={slug}>
                <Link to={aboutTopicPath(slug)} className="about-not-link tap-target">
                  {line}
                  <span className="about-not-cta">{learnMore}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </section>

      <section className="about-section about-method">
        <div className="about-section-head">
          <h3 className="about-section-title">{t('about.methodTitle')}</h3>
        </div>
        <ol className="about-method-steps">
          {methodSteps.map((step, i) => {
            const slug = ABOUT_METHOD_SLUGS[i]
            return (
              <li key={slug}>
                <Link to={aboutTopicPath(slug)} className="about-method-link tap-target">
                  {step}
                  <span className="about-method-cta">{learnMore}</span>
                </Link>
              </li>
            )
          })}
        </ol>
      </section>

      <section className="about-contact-teaser">
        <div className="about-contact-inner">
          <span className="page-eyebrow">{t('about.contactEyebrow')}</span>
          <h3 className="about-contact-title">{t('about.contactTitle')}</h3>
          <p>{t('about.contactBody')}</p>
          <div className="about-contact-chips">
            {chips.map((chip) => (
              <span key={chip} className="about-chip about-chip-soon">
                {chip}
              </span>
            ))}
          </div>
        </div>
      </section>

      <footer className="about-disclaimer">
        <p>{t('about.disclaimer')}</p>
      </footer>
    </div>
  )
}
