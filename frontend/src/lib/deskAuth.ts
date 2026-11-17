const STORAGE_KEY = 'cyclical-desk-token'

export function readDeskToken(): string {
  try {
    return sessionStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function writeDeskToken(value: string): void {
  sessionStorage.setItem(STORAGE_KEY, value.trim())
  window.dispatchEvent(new Event('desk-auth'))
}

export function clearDeskToken(): void {
  sessionStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event('desk-auth'))
}

export function deskAuthHeaders(method: string, headers?: HeadersInit): Headers {
  const next = new Headers(headers)
  const verb = method.toUpperCase()
  if (verb !== 'GET' && verb !== 'HEAD' && verb !== 'OPTIONS') {
    const token = readDeskToken()
    if (token) next.set('X-Desk-Token', token)
  }
  return next
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = deskAuthHeaders(init.method || 'GET', init.headers)
  return globalThis.fetch(input, { ...init, headers })
}
