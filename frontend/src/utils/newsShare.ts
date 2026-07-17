export type SharePlatform =
  | 'native'
  | 'x'
  | 'facebook'
  | 'linkedin'
  | 'whatsapp'
  | 'telegram'
  | 'reddit'
  | 'bluesky'
  | 'substack'
  | 'email'
  | 'copy'

export const SHARE_PLATFORMS: SharePlatform[] = [
  'native',
  'x',
  'linkedin',
  'reddit',
  'substack',
  'facebook',
  'whatsapp',
  'telegram',
  'bluesky',
  'email',
  'copy',
]

export function shareText(title: string, source?: string): string {
  return source ? `${title} — ${source}` : title
}

export function buildShareUrl(platform: SharePlatform, title: string, url: string): string | null {
  const encodedUrl = encodeURIComponent(url)
  const encodedTitle = encodeURIComponent(title)
  const line = encodeURIComponent(url ? `${title} ${url}` : title)

  switch (platform) {
    case 'x':
      return url
        ? `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`
        : `https://twitter.com/intent/tweet?text=${encodedTitle}`
    case 'facebook':
      return url ? `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}` : null
    case 'linkedin':
      return url ? `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}` : null
    case 'whatsapp':
      return `https://wa.me/?text=${line}`
    case 'telegram':
      return url
        ? `https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`
        : `https://t.me/share/url?url=&text=${encodedTitle}`
    case 'reddit':
      return url
        ? `https://www.reddit.com/submit?url=${encodedUrl}&title=${encodedTitle}`
        : `https://www.reddit.com/submit?title=${encodedTitle}`
    case 'bluesky':
      return `https://bsky.app/intent/compose?text=${line}`
    case 'email':
      return url
        ? `mailto:?subject=${encodedTitle}&body=${encodeURIComponent(`${title}\n\n${url}`)}`
        : `mailto:?subject=${encodedTitle}&body=${encodedTitle}`
    default:
      return null
  }
}

export function canNativeShare(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

export async function nativeShare(title: string, url?: string | null): Promise<boolean> {
  if (!canNativeShare()) return false
  try {
    await navigator.share(url ? { title, url } : { title, text: title })
    return true
  } catch {
    return false
  }
}

export async function copyShareLink(title: string, url?: string | null): Promise<boolean> {
  const text = url ? `${title}\n${url}` : title
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}
