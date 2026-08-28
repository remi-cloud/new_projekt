/** Server-side outbound redirect — unwraps Google RSS wrappers on click. */
export function newsOutboundUrl(newsId: string): string {
  return `/api/news/out/${encodeURIComponent(newsId)}`
}

export function newsShareUrl(newsId: string): string {
  const path = newsOutboundUrl(newsId)
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${path}`
  }
  return path
}
