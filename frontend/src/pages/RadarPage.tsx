import { Link } from 'react-router-dom'
import {
  RADAR_EDGES,
  RADAR_KIND_COLOR,
  RADAR_NODES,
  RADAR_PUBLISHED,
  RADAR_SOURCE,
} from '../data/radarPublic'
import { useLocale } from '../context/LocaleContext'

const byId = Object.fromEntries(RADAR_NODES.map((node) => [node.id, node]))

export function RadarPage() {
  const { t } = useLocale()
  return (
    <div className="radar-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('radarPage.eyebrow')}</span>
        <h2 className="page-headline">{t('radarPage.title')}</h2>
        <p className="page-lead">{t('radarPage.lead')}</p>
        <div className="astra-math-links">
          <a className="btn tap-target" href="https://www.ic3.gov/" target="_blank" rel="noopener noreferrer">
            {t('radarPage.reportIc3')}
          </a>
          <a className="btn btn-ghost tap-target" href="https://incydent.cert.pl/" target="_blank" rel="noopener noreferrer">
            {t('radarPage.cert')}
          </a>
          <a className="btn btn-ghost tap-target" href={RADAR_SOURCE} target="_blank" rel="noopener noreferrer">
            {t('radarPage.source')}
          </a>
          <Link className="btn btn-ghost tap-target" to="/ai-hacking">
            {t('radarPage.aiLink')}
          </Link>
        </div>
      </header>

      <section className="radar-map" aria-label={t('radarPage.mapLabel')}>
        <svg viewBox="0 0 720 280" role="img">
          <title>{t('radarPage.mapTitle')}</title>
          {RADAR_EDGES.map(([a, b]) => {
            const from = byId[a]
            const to = byId[b]
            return (
              <line
                key={`${a}-${b}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                className="radar-edge"
              />
            )
          })}
          {RADAR_NODES.map((node) => (
            <g key={node.id}>
              <circle cx={node.x} cy={node.y} r="8" fill={RADAR_KIND_COLOR[node.kind] || '#ccc'}>
                <title>
                  {node.net} {node.kind}: {node.label} · {node.score}/100
                </title>
              </circle>
              <text x={node.x + 12} y={node.y + 4}>
                {node.label}
              </text>
            </g>
          ))}
        </svg>
        <p className="radar-note">{t('radarPage.note', { date: RADAR_PUBLISHED })}</p>
      </section>

      <div className="ai-hack-grid">
        <article className="ai-hack-card">
          <h4>{t('radarPage.s1Title')}</h4>
          <p>{t('radarPage.s1Body')}</p>
        </article>
        <article className="ai-hack-card">
          <h4>{t('radarPage.s2Title')}</h4>
          <p>{t('radarPage.s2Body')}</p>
        </article>
        <article className="ai-hack-card">
          <h4>{t('radarPage.scoreTitle')}</h4>
          <p>{t('radarPage.scoreBody')}</p>
        </article>
        <article className="ai-hack-card">
          <h4>{t('radarPage.archTitle')}</h4>
          <p>{t('radarPage.archBody')}</p>
        </article>
      </div>

      <footer className="about-disclaimer">
        <p>{t('radarPage.disclaimer')}</p>
      </footer>
    </div>
  )
}
