import {
  AlertLogEntry,
  AlertSettings,
  DashboardResponse,
  HistoryResponse,
  SuperOpportunitiesResponse,
  WatchlistItem,
  WatchlistResponse,
} from './types'

const API_BASE = '/api'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    let detail = `Błąd API (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

async function sendJson<T>(path: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Błąd API (${res.status})`)
  }
  return res.json()
}

export async function fetchDashboard(): Promise<DashboardResponse> {
  return getJson<DashboardResponse>('/dashboard')
}

export async function triggerScan(): Promise<{
  scanned: boolean
  opportunities_count: number
  changes_count: number
}> {
  return sendJson('/scan', 'POST')
}

export async function fetchHistory(): Promise<HistoryResponse> {
  return getJson<HistoryResponse>('/history')
}

export async function fetchWatchlist(): Promise<WatchlistResponse> {
  return getJson<WatchlistResponse>('/watchlist')
}

export async function addWatchlistItem(payload: {
  symbol: string
  name?: string
  asset_class?: string
}): Promise<WatchlistItem> {
  return sendJson('/watchlist', 'POST', payload)
}

export async function removeWatchlistItem(symbol: string): Promise<void> {
  await sendJson(`/watchlist/${encodeURIComponent(symbol)}`, 'DELETE')
}

export async function toggleWatchlistItem(symbol: string, enabled: boolean): Promise<WatchlistItem> {
  return sendJson(`/watchlist/${encodeURIComponent(symbol)}`, 'PATCH', { enabled })
}

export async function resetWatchlist(): Promise<{ items: WatchlistItem[] }> {
  return sendJson('/watchlist/reset', 'POST')
}

export async function fetchAlertSettings(): Promise<AlertSettings> {
  return getJson<AlertSettings>('/alerts/settings')
}

export async function saveAlertSettings(settings: AlertSettings): Promise<AlertSettings> {
  return sendJson('/alerts/settings', 'PUT', settings)
}

export async function fetchAlertLog(): Promise<AlertLogEntry[]> {
  return getJson<AlertLogEntry[]>('/alerts/log')
}

export async function testAlert(): Promise<{ ok: boolean; detail?: string }> {
  return sendJson('/alerts/test', 'POST')
}

export async function fetchSuperOpportunities(
  minScore = 0,
): Promise<SuperOpportunitiesResponse> {
  return getJson<SuperOpportunitiesResponse>(`/super-opportunities?min_score=${minScore}`)
}
