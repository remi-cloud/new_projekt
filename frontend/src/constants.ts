export const ASSET_LABELS = {
  crypto: 'Krypto',
  stock: 'Akcje',
  index: 'Indeksy',
  bond: 'Obligacje',
  commodity: 'Surowce',
  forex: 'Forex',
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
}

export const NAV_ITEMS = [
  { path: '/', label: 'Start', icon: '⌂' },
  { path: '/dashboard', label: 'Dashboard', icon: '◫' },
  { path: '/cykle', label: 'Cykle', icon: '↻' },
  { path: '/okazje', label: 'Okazje', icon: '◎' },
  { path: '/rynki', label: 'Rynki', icon: '▤' },
  { path: '/o-aplikacji', label: 'O aplikacji', icon: 'i' },
]
