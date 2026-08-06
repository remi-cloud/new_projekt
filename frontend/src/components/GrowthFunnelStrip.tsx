import { Link } from 'react-router-dom'
import { NewsletterSignup } from './NewsletterSignup'
import { useLocale } from '../context/LocaleContext'

type Props = {
  source: string
}

/** Shared growth funnel — newsletter + Live/Biznes CTAs on info pages. */
export function GrowthFunnelStrip({ source }: Props) {
  const { t } = useLocale()

  return (
    <section className="growth-home-strip growth-funnel-strip">
      <div>
        <h3>{t('growth.homeStripTitle')}</h3>
        <p>{t('growth.homeStripLead')}</p>
      </div>
      <div className="growth-home-links">
        <Link to="/live" className="btn tap-target">
          {t('growth.ctaLive')}
        </Link>
        <Link to="/biznes" className="btn btn-ghost tap-target">
          {t('growth.ctaBiz')}
        </Link>
        <Link to="/partnerzy" className="btn btn-ghost tap-target">
          {t('nav.partners')}
        </Link>
      </div>
      <NewsletterSignup source={source} compact />
    </section>
  )
}
