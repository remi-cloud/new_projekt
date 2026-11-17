import { navActivePath, sectionForPath } from '../constants'
import type { TranslationPath } from '../i18n'

const KNOWN: Record<string, TranslationPath> = {
  '/': 'nav.start',
  '/dashboard': 'nav.panel',
  '/rynki': 'nav.markets',
  '/okazje': 'nav.opportunities',
  '/superokazje': 'nav.super',
  '/cykle': 'nav.cycles',
  '/kalkulator': 'nav.calculator',
  '/live': 'nav.live',
  '/biznes': 'nav.business',
  '/partnerzy': 'nav.partners',
  '/embed': 'nav.embed',
  '/news': 'nav.news',
  '/ai-hacking': 'nav.aiHacking',
  '/radar': 'nav.radar',
  '/agent': 'nav.agent',
  '/narzedzia': 'nav.tools',
  '/narzedzia/singularity': 'nav.singularity',
  '/narzedzia/astra': 'nav.astra',
  '/execution': 'nav.execution',
  '/powiadomienia': 'nav.alerts',
  '/o-nas': 'nav.about',
  '/portfel': 'nav.portfolio',
  '/perly': 'nav.pearls',
  '/fomo': 'nav.fomo',
  '/axiom': 'nav.axiom',
  '/launch': 'nav.launch',
  '/logowanie': 'layout.loginTitle',
}

export function symbolFromDeskPath(pathname: string): string | null {
  const match = pathname.match(/^\/(?:pozycja|superokazje)\/(.+)$/)
  if (!match) return null
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

export function shellTitle(pathname: string, t: (path: TranslationPath) => string): string {
  const symbol = symbolFromDeskPath(pathname)
  if (symbol) return symbol
  if (pathname.startsWith('/o-nas')) return t('nav.about')
  const active = navActivePath(pathname)
  const section = sectionForPath(pathname)
  const link = section?.items.find((item) => item.path === active)
  if (link) return t(link.labelKey)
  if (KNOWN[pathname]) return t(KNOWN[pathname])
  if (pathname === '/') return t('nav.start')
  return t('layout.notFoundTitle')
}
