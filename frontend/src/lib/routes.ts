/** Deep-link to position detail (same view as Superokazje). */
export function positionPath(symbol: string): string {
  return `/superokazje/${encodeURIComponent(symbol)}`
}
