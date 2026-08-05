/** Deep-link to Superokazje position detail. */
export function positionPath(symbol: string): string {
  return `/superokazje/${encodeURIComponent(symbol)}`
}
