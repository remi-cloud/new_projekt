import { Link, useLocation } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from '../i18n'

export type SectionTab = {
  path: string
  labelKey: TranslationPath
}

function isTabActive(pathname: string, tabPath: string, tabs: SectionTab[]): boolean {
  if (pathname === tabPath) return true
  if (tabPath === '/' || !pathname.startsWith(`${tabPath}/`)) return false
  // Prefer the most specific tab (e.g. /narzedzia/singularity over /narzedzia)
  const longerMatch = tabs.some(
    (other) =>
      other.path !== tabPath &&
      other.path.startsWith(`${tabPath}/`) &&
      (pathname === other.path || pathname.startsWith(`${other.path}/`)),
  )
  return !longerMatch
}

export function SectionTabs({ tabs }: { tabs: SectionTab[] }) {
  const location = useLocation()
  const { t } = useLocale()
  if (tabs.length < 2) return null

  return (
    <nav className="section-tabs" aria-label={t('layout.navMain')}>
      {tabs.map((tab) => {
        const active = isTabActive(location.pathname, tab.path, tabs)
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
