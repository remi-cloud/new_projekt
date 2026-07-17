/** Share links for instruments, paper positions and pearl finds. */

import type { TranslationPath } from '../i18n'

export type InstrumentShareKind = 'instrument' | 'position' | 'pearl'

export function instrumentPageUrl(symbol: string): string {
  if (typeof window === 'undefined') return `/instrument/${encodeURIComponent(symbol)}`
  return `${window.location.origin}/instrument/${encodeURIComponent(symbol)}`
}

export function buildInstrumentShareTitle(
  kind: InstrumentShareKind,
  params: {
    name: string
    symbol: string
    signal?: string
    side?: string
    pnlPct?: number
  },
  t: (path: TranslationPath, vars?: Record<string, string | number>) => string,
): string {
  const { name, symbol, signal, side, pnlPct } = params
  if (kind === 'pearl') {
    return t('instrument.sharePearl', {
      name,
      symbol,
      signal: signal ?? '—',
    })
  }
  if (kind === 'position') {
    const pnl =
      pnlPct != null
        ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}`
        : '—'
    return t('instrument.sharePosition', {
      name,
      symbol,
      side: side ?? '—',
      pnl,
    })
  }
  return t('instrument.shareInstrument', {
    name,
    symbol,
    signal: signal ?? '—',
  })
}
