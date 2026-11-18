import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAiAcademy, type AiAcademy } from '../api'
import { ErrorState } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'

const PART_LABEL: Record<string, string> = {
  ai: 'AI',
  nauka: 'Nauka',
  security: 'Cyberbezpieczeństwo',
}

export function AiHackingPage() {
  const { t } = useLocale()
  const [data, setData] = useState<AiAcademy | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [partId, setPartId] = useState('ai')

  const load = () => {
    setError(null)
    fetchAiAcademy()
      .then(setData)
      .catch(() => setError(t('aiHacking.loadError')))
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    if (!data?.parts.length) return
    if (!data.parts.some((part) => part.id === partId)) setPartId(data.parts[0].id)
  }, [data, partId])

  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return <div className="page-loading">{t('aiHacking.loading')}</div>

  return (
    <div className="ai-hack-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{data.eyebrow}</span>
        <h2 className="page-headline">{data.title}</h2>
        <p className="page-lead">{data.lead}</p>
        <Link className="ai-hack-link tap-target" to="/radar">
          <strong>Radar oszustw</strong>
          <span>Mapa siatek z lokalnego radaru na Archu. Identyfikatory bez linków do sprawców.</span>
        </Link>
      </header>

      <div className="filter-chips" role="tablist">
        {data.parts.map((part) => (
          <button
            key={part.id}
            type="button"
            role="tab"
            aria-selected={partId === part.id}
            className={`chip${partId === part.id ? ' active' : ''}`}
            onClick={() => setPartId(part.id)}
          >
            {PART_LABEL[part.id] ?? part.title}
          </button>
        ))}
      </div>

      {data.parts.filter((part) => part.id === partId).map((part) => (
        <section key={part.id} className="ai-hack-part" aria-labelledby={`ai-hack-${part.id}`}>
          <div className="about-section-head">
            <h3 id={`ai-hack-${part.id}`} className="about-section-title">
              {part.title}
            </h3>
            <p className="about-section-desc">{part.lead}</p>
          </div>
          <div className="ai-hack-grid">
            {part.sections.map((section) => (
              <article key={section.title} className="ai-hack-card">
                <h4>{section.title}</h4>
                <p>{section.body}</p>
              </article>
            ))}
          </div>
          {part.links && part.links.length > 0 && (
            <div className="ai-hack-links">
              {part.links.map((link) =>
                link.href.startsWith('/') ? (
                  <Link key={link.href} className="ai-hack-link tap-target" to={link.href}>
                    <strong>{link.label}</strong>
                    {link.note && <span>{link.note}</span>}
                  </Link>
                ) : (
                  <a
                    key={link.href}
                    className="ai-hack-link tap-target"
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <strong>{link.label}</strong>
                    {link.note && <span>{link.note}</span>}
                  </a>
                ),
              )}
            </div>
          )}
        </section>
      ))}

      <footer className="about-disclaimer">
        <p>{data.disclaimer}</p>
      </footer>
    </div>
  )
}
