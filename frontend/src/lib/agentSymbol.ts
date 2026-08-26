/** Frontend symbol aliases — keep in sync with backend SYMBOL_ALIASES for UX. */
export const AGENT_SYMBOL_ALIASES: Record<string, string> = {
  btc: 'BTC-USD',
  bitcoin: 'BTC-USD',
  eth: 'ETH-USD',
  ethereum: 'ETH-USD',
  sol: 'SOL-USD',
  sp500: '^GSPC',
  nasdaq: '^IXIC',
  gold: 'GC=F',
  oil: 'CL=F',
  spacex: 'SPCX',
  'space-x': 'SPCX',
  spcx: 'SPCX',
  liq: 'LQD',
}

export type ResolveAgentSymbolResult =
  | { ok: true; symbol: string; aliasedFrom?: string }
  | { ok: false; reason: 'empty' | 'unknown'; input: string }

/** Normalize typed toolbar symbol against aliases + known catalog. */
export function resolveAgentSymbol(
  raw: string,
  knownSymbols: Iterable<string>,
): ResolveAgentSymbolResult {
  const input = raw.trim()
  if (!input) return { ok: false, reason: 'empty', input }

  const known = new Set([...knownSymbols].map((s) => s.toUpperCase()))
  const low = input.toLowerCase()
  const aliased = AGENT_SYMBOL_ALIASES[low]
  if (aliased) {
    return { ok: true, symbol: aliased, aliasedFrom: input.toUpperCase() }
  }

  const upper = input.toUpperCase().replace(/\s+/g, '')
  if (known.size === 0) {
    // Catalog not loaded yet — accept after alias pass (don't hard-block).
    return { ok: true, symbol: upper }
  }
  if (known.has(upper)) return { ok: true, symbol: upper }

  // BTC ↔ BTC-USD style
  if (known.has(`${upper}-USD`)) return { ok: true, symbol: `${upper}-USD` }
  if (upper.endsWith('-USD')) {
    const base = upper.slice(0, -4)
    if (known.has(base)) return { ok: true, symbol: base }
  }

  return { ok: false, reason: 'unknown', input: upper }
}
