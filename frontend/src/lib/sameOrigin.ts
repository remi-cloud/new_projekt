/**
 * Same-origin API root.
 * `VITE_API_BASE` may be an absolute origin (Render) or empty.
 * A loopback origin baked in at build time is ignored so production
 * keeps calling `/api` on whatever host actually served the page.
 */
const LOOPBACK_8080 = /^https?:\/\/(?:127\.0\.0\.1|localhost):8080(?=\/|$)/i

export function stripLoopbackOrigin(url: string): string {
  const trimmed = url.trim()
  const match = trimmed.match(LOOPBACK_8080)
  if (!match) return trimmed
  const rest = trimmed.slice(match[0].length)
  if (!rest) return ''
  return rest.startsWith('/') ? rest : `/${rest}`
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_BASE ?? '').trim()
  if (!raw) return ''
  const stripped = stripLoopbackOrigin(raw).replace(/\/$/, '')
  if (!stripped || stripped === '/api') return ''
  return stripped
}

const root = apiRoot()
export const API_BASE = root ? `${root}/api` : '/api'
