import { Link } from 'react-router-dom'
import {
  ASTRA_ADVANCES,
  ASTRA_MANUSCRIPT_URL,
  ASTRA_SOURCE_URL,
  type AstraField,
} from '../data/astraMathAdvances'
import { MATH_FINANCE_GLOSSARY } from '../data/mathFinanceGlossary'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from '../i18n'

export default function AstraMathPage() {
  const { t } = useLocale()

  return (
    <div className="astra-math-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('astraMath.eyebrow')}</span>
        <h2 className="page-headline">{t('astraMath.title')}</h2>
        <p className="page-lead">{t('astraMath.lead')}</p>
        <div className="astra-math-links">
          <a
            className="btn tap-target"
            href={ASTRA_SOURCE_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('astraMath.source')}
          </a>
          <a
            className="btn btn-ghost tap-target"
            href={ASTRA_MANUSCRIPT_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('astraMath.manuscript')}
          </a>
          <Link to="/narzedzia" className="btn btn-ghost tap-target">
            {t('astraMath.backTools')}
          </Link>
        </div>
      </header>

      <p className="astra-math-note">{t('astraMath.leanNote')}</p>

      <ol className="astra-math-grid">
        {ASTRA_ADVANCES.map((a) => {
          const titleKey = `astraMath.items.${a.id}.title` as TranslationPath
          const summaryKey = `astraMath.items.${a.id}.summary` as TranslationPath
          const financeKey = `astraMath.items.${a.id}.finance` as TranslationPath
          const marketKey = `astraMath.items.${a.id}.market` as TranslationPath
          const fieldKey = `astraMath.fields.${a.field as AstraField}` as TranslationPath
          return (
            <li key={a.id} className="astra-math-card">
              <div className="astra-math-card-top">
                <span className="astra-math-n">{String(a.n).padStart(2, '0')}</span>
                <span className="astra-math-field">{t(fieldKey)}</span>
              </div>
              <h3>{t(titleKey)}</h3>
              <p>{t(summaryKey)}</p>
              <div className="astra-math-translate">
                <p>
                  <strong>{t('astraMath.financeLabel')}</strong> {t(financeKey)}
                </p>
                <p>
                  <strong>{t('astraMath.marketLabel')}</strong> {t(marketKey)}
                </p>
              </div>
            </li>
          )
        })}
      </ol>

      <section className="astra-glossary" aria-labelledby="astra-glossary-title">
        <h3 id="astra-glossary-title">{t('astraMath.glossaryTitle')}</h3>
        <p className="astra-math-note">{t('astraMath.glossaryLead')}</p>
        <div className="astra-glossary-grid">
          {MATH_FINANCE_GLOSSARY.map((id) => (
            <article key={id} className="astra-glossary-card">
              <h4>{id}</h4>
              <p>
                <strong>Math.</strong>{' '}
                {t(`astraMath.glossary.${id}.math` as TranslationPath)}
              </p>
              <p>
                <strong>{t('astraMath.financeLabel')}</strong>{' '}
                {t(`astraMath.glossary.${id}.finance` as TranslationPath)}
              </p>
              <p>
                <strong>{t('astraMath.marketLabel')}</strong>{' '}
                {t(`astraMath.glossary.${id}.market` as TranslationPath)}
              </p>
            </article>
          ))}
        </div>
      </section>

      <p className="growth-disclaimer">{t('astraMath.disclaimer')}</p>
    </div>
  )
}
