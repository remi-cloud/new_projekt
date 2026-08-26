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

/** Primary sidebar entries — hubs expand into section tabs, not extra sidebar rows. */
export const NAV_ITEMS: { path: string; labelKey: TranslationPath }[] = [
  { path: '/', labelKey: 'nav.start' },
  { path: '/dashboard', labelKey: 'nav.panel' },
  { path: '/live', labelKey: 'nav.live' },
  { path: '/rynki', labelKey: 'nav.markets' },
  { path: '/narzedzia', labelKey: 'nav.tools' },
  { path: '/news', labelKey: 'nav.news' },
  { path: '/biznes', labelKey: 'nav.business' },
  { path: '/powiadomienia', labelKey: 'nav.alerts' },
  { path: '/o-nas', labelKey: 'nav.about' },
]

export type NavHub = {
  id: string
  /** Sidebar path used for this hub entry */
  root: string
  tabs: { path: string; labelKey: TranslationPath }[]
}

export const NAV_HUBS: NavHub[] = [
  {
    id: 'markets',
    root: '/rynki',
    tabs: [
      { path: '/rynki', labelKey: 'nav.markets' },
      { path: '/okazje', labelKey: 'nav.opportunities' },
      { path: '/superokazje', labelKey: 'nav.super' },
      { path: '/perly', labelKey: 'nav.pearls' },
      { path: '/fomo', labelKey: 'nav.fomo' },
      { path: '/axiom', labelKey: 'nav.axiom' },
      { path: '/launch', labelKey: 'nav.launch' },
      { path: '/cykle', labelKey: 'nav.cycles' },
    ],
  },
  {
    id: 'tools',
    root: '/narzedzia',
    tabs: [
      { path: '/narzedzia', labelKey: 'nav.toolsCatalog' },
      { path: '/narzedzia/singularity', labelKey: 'nav.singularity' },
      { path: '/narzedzia/astra', labelKey: 'nav.astra' },
      { path: '/agent', labelKey: 'nav.agent' },
      { path: '/fomo', labelKey: 'nav.fomo' },
      { path: '/axiom', labelKey: 'nav.axiom' },
      { path: '/launch', labelKey: 'nav.launch' },
      { path: '/execution', labelKey: 'nav.execution' },
      { path: '/kalkulator', labelKey: 'nav.calculator' },
    ],
  },
  {
    id: 'growth',
    root: '/biznes',
    tabs: [
      { path: '/biznes', labelKey: 'nav.business' },
      { path: '/partnerzy', labelKey: 'nav.partners' },
    ],
  },
]

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

/** Resolve which sidebar item should look active for the current URL. */
export function navActivePath(pathname: string): string {
  const hub = hubForPath(pathname)
  if (hub) return hub.root
  if (pathname.startsWith('/o-nas')) return '/o-nas'
  if (pathname.startsWith('/embed')) return '/biznes'
  if (pathname.startsWith('/instrument')) return '/rynki'
  return pathname
}

export const MOBILE_NAV = [
  { path: '/', label: 'Start', icon: '⌂' },
  { path: '/dashboard', label: 'Panel', icon: '◫' },
  { path: '/portfel', label: 'Portfel', icon: '₿' },
  { path: '/rynki', label: 'Rynki', icon: '▤' },
  { path: '/okazje', label: 'Okazje', icon: '◎' },
]
