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

export function writeDeskToken(_value: string): void {
  dropLegacyToken()
  window.dispatchEvent(new Event('desk-auth'))
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
