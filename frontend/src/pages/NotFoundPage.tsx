import { Link } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'

export function NotFoundPage() {
  const { t } = useLocale()

  return (
    <div className="institutional-page not-found-page">
      <header className="page-intro">
        <span className="page-eyebrow">404</span>
        <h2 className="page-headline">{t('layout.notFoundTitle')}</h2>
        <p className="page-lead">{t('layout.notFoundLead')}</p>
      </header>
      <Link className="btn btn-primary" to="/">
        {t('layout.notFoundHome')}
      </Link>
    </div>
  )
}
