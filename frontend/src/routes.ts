/** English / legacy aliases → canonical Polish (or shared) paths. */
export const ALIAS_REDIRECTS: { from: string; to: string }[] = [
  { from: 'business', to: '/biznes' },
  { from: 'partners', to: '/partnerzy' },
  { from: 'calculator', to: '/kalkulator' },
  { from: 'roi', to: '/kalkulator' },
  { from: 'markets', to: '/rynki' },
  { from: 'alerts', to: '/powiadomienia' },
  { from: 'about', to: '/o-nas' },
  { from: 'portfolio', to: '/portfel' },
  { from: 'cycles', to: '/cykle' },
  { from: 'opportunities', to: '/okazje' },
  { from: 'super', to: '/superokazje' },
  { from: 'tools', to: '/narzedzia' },
  { from: 'ai', to: '/agent' },
  { from: 'panel', to: '/dashboard' },
  { from: 'home', to: '/' },
  { from: 'start', to: '/' },
  { from: 'telegram', to: '/biznes' },
  { from: 'discord', to: '/biznes' },
  { from: 'channels', to: '/biznes' },
  { from: 'kanaly', to: '/biznes' },
]

/** Used by FastAPI hard redirects (path without leading slash). */
export const SERVER_REDIRECTS: Record<string, string> = Object.fromEntries(
  ALIAS_REDIRECTS.map(({ from, to }) => [from, to]),
)
