import { API_BASE } from './sameOrigin'

const LEGACY_STORAGE_KEY = 'cyclical-desk-token'

function dropLegacyToken(): void {
  try {
    sessionStorage.removeItem(LEGACY_STORAGE_KEY)
  } catch {
    /* private mode */
  }
}

export function readDeskToken(): string {
  dropLegacyToken()
  return ''
}

export async function deskSessionOpen(): Promise<boolean> {
  dropLegacyToken()
  try {
    const res = await apiFetch(`${API_BASE}/desk/status`)
    if (!res.ok) return false
    const body = (await res.json()) as { authenticated?: boolean }
    return Boolean(body.authenticated)
  } catch {
    return false
  }
}

export function writeDeskToken(_value: string): void {
  dropLegacyToken()
  window.dispatchEvent(new Event('desk-auth'))
}

export function noteDeskSession(): void {
  writeDeskToken('')
}

export function clearDeskToken(): void {
  dropLegacyToken()
  window.dispatchEvent(new Event('desk-auth'))
  void globalThis
    .fetch(`${API_BASE}/desk/logout`, { method: 'POST', credentials: 'include' })
    .catch(() => undefined)
}

export function deskAuthHeaders(_method: string, headers?: HeadersInit): Headers {
  return new Headers(headers)
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = deskAuthHeaders(init.method || 'GET', init.headers)
  return globalThis.fetch(input, { ...init, headers, credentials: 'include' })
}
