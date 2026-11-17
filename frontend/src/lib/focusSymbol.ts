function keys(symbol: string): string[] {
  const up = decodeSymbol(symbol).toUpperCase()
  const withoutQuote = up.replace(/-(USD|USDT)$/, '')
  const root = up.split(/[=./]/)[0]
  return [...new Set([up, withoutQuote, root].filter(Boolean))]
}

export function decodeSymbol(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

/** True when a route symbol names this instrument, including BTC → BTC-USD. */
export function focusMatches(routeSymbol: string | null | undefined, symbol: string): boolean {
  if (!routeSymbol) return false
  const route = new Set(keys(routeSymbol))
  return keys(symbol).some((key) => route.has(key))
}

export function focusedSymbol(routeSymbol: string | null | undefined, symbols: string[]): string | null {
  if (!routeSymbol || symbols.length === 0) return null
  const exact = symbols.find((symbol) => decodeSymbol(routeSymbol).toUpperCase() === symbol.toUpperCase())
  if (exact) return exact
  return symbols.find((symbol) => focusMatches(routeSymbol, symbol)) ?? null
}
