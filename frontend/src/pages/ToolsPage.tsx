import { Link } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from '../i18n'

type ToolDef = {
  id: 'singularity' | 'astra' | 'agent' | 'execution' | 'calculator' | 'super' | 'pearls' | 'fomo' | 'axiom' | 'launch' | 'news'
  to: string
  nameKey: TranslationPath
  blurbKey: TranslationPath
  group: 'ai' | 'desk' | 'trade'
}

const TOOLS: ToolDef[] = [
  {
    id: 'launch',
    to: '/launch',
    nameKey: 'tools.items.launch.name',
    blurbKey: 'tools.items.launch.blurb',
    group: 'ai',
  },
  {
    id: 'axiom',
    to: '/axiom',
    nameKey: 'tools.items.axiom.name',
    blurbKey: 'tools.items.axiom.blurb',
    group: 'ai',
  },
  {
    id: 'singularity',
    to: '/narzedzia/singularity',
    nameKey: 'tools.items.singularity.name',
    blurbKey: 'tools.items.singularity.blurb',
    group: 'ai',
  },
  {
    id: 'astra',
    to: '/narzedzia/astra',
    nameKey: 'tools.items.astra.name',
    blurbKey: 'tools.items.astra.blurb',
    group: 'ai',
  },
  {
    id: 'agent',
    to: '/agent',
    nameKey: 'tools.items.agent.name',
    blurbKey: 'tools.items.agent.blurb',
    group: 'ai',
  },
  {
    id: 'fomo',
    to: '/fomo',
    nameKey: 'tools.items.fomo.name',
    blurbKey: 'tools.items.fomo.blurb',
    group: 'ai',
  },
  {
    id: 'execution',
    to: '/execution',
    nameKey: 'tools.items.execution.name',
    blurbKey: 'tools.items.execution.blurb',
    group: 'trade',
  },
  {
    id: 'calculator',
    to: '/kalkulator',
    nameKey: 'tools.items.calculator.name',
    blurbKey: 'tools.items.calculator.blurb',
    group: 'desk',
  },
  {
    id: 'super',
    to: '/superokazje',
    nameKey: 'tools.items.super.name',
    blurbKey: 'tools.items.super.blurb',
    group: 'desk',
  },
  {
    id: 'pearls',
    to: '/perly',
    nameKey: 'tools.items.pearls.name',
    blurbKey: 'tools.items.pearls.blurb',
    group: 'desk',
  },
  {
    id: 'news',
    to: '/news',
    nameKey: 'tools.items.news.name',
    blurbKey: 'tools.items.news.blurb',
    group: 'desk',
  },
]

const GROUPS: { id: ToolDef['group']; titleKey: TranslationPath }[] = [
  { id: 'ai', titleKey: 'tools.groups.ai' },
  { id: 'desk', titleKey: 'tools.groups.desk' },
  { id: 'trade', titleKey: 'tools.groups.trade' },
]

export default function ToolsPage() {
  const { t } = useLocale()

  return (
    <div className="tools-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('tools.eyebrow')}</span>
        <h2 className="page-headline">{t('tools.title')}</h2>
        <p className="page-lead">{t('tools.lead')}</p>
      </header>

      {GROUPS.map((group) => {
        const items = TOOLS.filter((tool) => tool.group === group.id)
        if (!items.length) return null
        return (
          <section key={group.id} className="tools-section" aria-labelledby={`tools-${group.id}`}>
            <h3 id={`tools-${group.id}`} className="tools-section-title">
              {t(group.titleKey)}
            </h3>
            <div className="tools-grid">
              {items.map((tool) => (
                <Link key={tool.id} to={tool.to} className="tool-card tap-target">
                  <span className="tool-card-tag">{t(`tools.tags.${tool.group}` as TranslationPath)}</span>
                  <strong>{t(tool.nameKey)}</strong>
                  <p>{t(tool.blurbKey)}</p>
                  <span className="tool-card-cta">{t('tools.open')}</span>
                </Link>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
