import { stripLoopbackOrigin } from './sameOrigin'

/** Server-side outbound redirect — unwraps Google RSS wrappers on click. */
export function newsOutboundUrl(newsId: string): string {
  return `/api/news/out/${encodeURIComponent(newsId)}`
}

/** Hero images and stored links must not pin the browser to the dev origin. */
export function newsAssetUrl(url: string | null | undefined): string {
  if (!url) return ''
  return stripLoopbackOrigin(url)
}

export function newsShareUrl(newsId: string): string {
  const path = newsOutboundUrl(newsId)
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${path}`
  }
  return path
}
