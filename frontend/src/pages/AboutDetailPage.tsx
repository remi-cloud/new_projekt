import { Link, Navigate, useParams } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import { translations } from '../i18n'
import { isAboutTopicSlug } from '../i18n/aboutTopics'

export function AboutDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const { locale } = useLocale()

  if (!slug || !isAboutTopicSlug(slug)) {
    return <Navigate to="/o-nas" replace />
  }

  const detail = translations[locale].aboutDetail
  const topic = detail.topics[slug]

  if (!topic) {
    return (
      <div className="about-detail-page institutional-page">
        <p>{detail.notFound}</p>
        <Link to="/o-nas" className="about-detail-back tap-target">
          {detail.back}
        </Link>
      </div>
    )
  }

  return (
    <div className="about-detail-page institutional-page">
      <Link to="/o-nas" className="about-detail-back tap-target">
        {detail.back}
      </Link>

      <header className="page-intro about-detail-header">
        <span className="page-eyebrow">{topic.eyebrow}</span>
        <h2 className="page-headline">{topic.title}</h2>
        <p className="page-lead">{topic.intro}</p>
      </header>

      <section className="about-detail-section">
        <h3 className="about-detail-section-title">{detail.howItWorks}</h3>
        <div className="about-detail-blocks">
          {topic.sections.map((section) => (
            <article key={section.title} className="about-detail-block">
              <h4>{section.title}</h4>
              <p>{section.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="about-detail-in-app">
        <h3 className="about-detail-section-title">{topic.inAppTitle}</h3>
        <p>{topic.inAppBody}</p>
      </section>
    </div>
  )
}
