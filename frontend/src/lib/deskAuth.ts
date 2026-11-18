import { API_BASE } from './sameOrigin'

const STORAGE_KEY = 'cyclical-desk-token'

function forgetStoredToken(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* private mode */
  }
}

/** Drop any token left by an older build. The session is an HttpOnly cookie. */
forgetStoredToken()

export function noteDeskSession(): void {
  forgetStoredToken()
  window.dispatchEvent(new Event('desk-auth'))
}

export function clearDeskToken(): void {
  forgetStoredToken()
  void fetch(`${API_BASE}/desk/logout`, { method: 'POST', credentials: 'same-origin' }).catch(() => undefined)
  window.dispatchEvent(new Event('desk-auth'))
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  return globalThis.fetch(input, { ...init, headers, credentials: 'same-origin' })
}
