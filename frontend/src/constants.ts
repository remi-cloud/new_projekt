import type { TranslationPath } from './i18n'

export const ASSET_LABELS = {
  crypto: 'Krypto',
  stock: 'Akcje',
  etf: 'ETF',
  index: 'Indeksy',
  bond: 'Obligacje',
  commodity: 'Surowce',
  forex: 'Forex',
} as const

export const REGION_LABELS = {
  global: 'Globalny',
  us: 'USA',
  eu: 'Europa',
  asia: 'Azja',
  em: 'Emerging',
  pl: 'Polska',
} as const

export const SIGNAL_LABELS = {
  buy: 'Kupuj',
  sell: 'Sprzedaj',
  hold: 'Trzymaj',
  watch: 'Obserwuj',
} as const

export const PHASE_LABELS: Record<string, string> = {
  bear: 'Spadkowa',
  accumulation: 'Akumulacja',
  bull: 'Wzrostowa',
  distribution: 'Dystrybucja',
  neutral: 'Neutralna',
  year_1: 'Rok 1',
  year_2: 'Rok 2',
  year_3: 'Rok 3',
  year_4: 'Rok 4',
  silne_wzrost: 'Silne wzrost',
  wzrost: 'Wzrost',
  silne_spadk: 'Silny spadek',
  spadek: 'Spadek',
  neutralne: 'Neutralne',
}

export type NavLink = { path: string; labelKey: TranslationPath }

export type NavSection = {
  id: string
  labelKey: TranslationPath
  items: NavLink[]
}

/** Grouped desk navigation. Section tabs mirror the same items.
 * AI stays first: PR #11 (07755c7) buried it under the long market list.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'ai',
    labelKey: 'nav.sectionAi',
    items: [
      { path: '/ai-hacking', labelKey: 'nav.aiHacking' },
      { path: '/radar', labelKey: 'nav.radar' },
    ],
  },
  {
    id: 'market',
    labelKey: 'nav.sectionMarket',
    items: [
      { path: '/dashboard', labelKey: 'nav.panel' },
      { path: '/okazje', labelKey: 'nav.opportunities' },
      { path: '/superokazje', labelKey: 'nav.super' },
      { path: '/rynki', labelKey: 'nav.scanner' },
      { path: '/perly', labelKey: 'nav.pearls' },
      { path: '/fomo', labelKey: 'nav.fomo' },
      { path: '/axiom', labelKey: 'nav.axiom' },
      { path: '/launch', labelKey: 'nav.launch' },
      { path: '/solana', labelKey: 'nav.solana' },
    ],
  },
  {
    id: 'cycles',
    labelKey: 'nav.sectionCycles',
    items: [
      { path: '/cykle', labelKey: 'nav.cycles' },
      { path: '/kalkulator', labelKey: 'nav.calculator' },
    ],
  },
  {
    id: 'news',
    labelKey: 'nav.sectionNews',
    items: [
      { path: '/news', labelKey: 'nav.news' },
      { path: '/live', labelKey: 'nav.live' },
    ],
  },
  {
    id: 'agent',
    labelKey: 'nav.sectionAgent',
    items: [
      { path: '/agent', labelKey: 'nav.agent' },
      { path: '/narzedzia', labelKey: 'nav.tools' },
      { path: '/narzedzia/singularity', labelKey: 'nav.singularity' },
      { path: '/narzedzia/astra', labelKey: 'nav.astra' },
      { path: '/execution', labelKey: 'nav.execution' },
    ],
  },
  {
    id: 'account',
    labelKey: 'nav.sectionAccount',
    items: [
      { path: '/portfel', labelKey: 'nav.portfolio' },
      { path: '/powiadomienia', labelKey: 'nav.alerts' },
      { path: '/biznes', labelKey: 'nav.business' },
      { path: '/partnerzy', labelKey: 'nav.partners' },
      { path: '/o-nas', labelKey: 'nav.about' },
    ],
  },
]

export const NAV_ITEMS: NavLink[] = NAV_SECTIONS.flatMap((section) => section.items)

export type NavHub = {
  id: string
  root: string
  tabs: NavLink[]
}

export const NAV_HUBS: NavHub[] = NAV_SECTIONS.map((section) => ({
  id: section.id,
  root: section.items[0].path,
  tabs: section.items,
}))

export function hubForPath(pathname: string): NavHub | undefined {
  // Prefer hub whose tab is the longest match (avoid /narzedzia stealing /narzedzia/singularity incorrectly across hubs)
  let best: NavHub | undefined
  let bestLen = -1
  for (const hub of NAV_HUBS) {
    for (const tab of hub.tabs) {
      const match =
        pathname === tab.path || (tab.path !== '/' && pathname.startsWith(`${tab.path}/`))
      if (match && tab.path.length > bestLen) {
        best = hub
        bestLen = tab.path.length
      }
    }
  }
  return best
}

/** Resolve which nav link should look active for the current URL. */
export function navActivePath(pathname: string): string {
  if (pathname.startsWith('/o-nas')) return '/o-nas'
  if (pathname.startsWith('/embed')) return '/biznes'
  if (pathname.startsWith('/instrument')) return '/rynki'
  if (pathname.startsWith('/pozycja')) return '/superokazje'
  let best = ''
  for (const item of NAV_ITEMS) {
    const match = pathname === item.path || pathname.startsWith(`${item.path}/`)
    if (match && item.path.length > best.length) best = item.path
  }
  return best || pathname
}

export function sectionForPath(pathname: string): NavSection | undefined {
  const active = navActivePath(pathname)
  return NAV_SECTIONS.find((section) => section.items.some((item) => item.path === active))
}

export const MOBILE_NAV: NavLink[] = [
  { path: '/dashboard', labelKey: 'nav.panel' },
  { path: '/ai-hacking', labelKey: 'nav.aiHacking' },
  { path: '/okazje', labelKey: 'nav.opportunities' },
  { path: '/rynki', labelKey: 'nav.scanner' },
  { path: '/portfel', labelKey: 'nav.portfolio' },
]
