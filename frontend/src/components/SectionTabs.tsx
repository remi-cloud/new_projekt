import { Link, useLocation } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from '../i18n'

export type SectionTab = {
  path: string
  labelKey: TranslationPath
}

export function SectionTabs({ tabs }: { tabs: SectionTab[] }) {
  const location = useLocation()
  const { t } = useLocale()
  if (tabs.length < 2) return null

  return (
    <nav className="section-tabs" aria-label={t('layout.navMain')}>
      {tabs.map((tab) => {
        const active =
          location.pathname === tab.path ||
          (tab.path !== '/' && location.pathname.startsWith(`${tab.path}/`))
        return (
          <Link
            key={tab.path}
            to={tab.path}
            className={`section-tab tap-target ${active ? 'active' : ''}`}
            aria-current={active ? 'page' : undefined}
          >
            {t(tab.labelKey)}
          </Link>
        )
      })}
    </nav>
  )
}
