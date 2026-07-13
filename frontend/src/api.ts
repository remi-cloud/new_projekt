import { AlertSettings, DashboardResponse, NotificationStatus, PaperOrderRequest, PaperPortfolio, TwilioConfig } from './types'
import { ChartPreset, ChartResponse, CHART_PRESETS } from './types/chart'

export { CHART_PRESETS }
export type { ChartPreset, ChartResponse }

export const API_BASE = '/api'

export async function fetchDashboard(): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/dashboard`)
  if (!res.ok) throw new Error('Nie udało się pobrać danych dashboardu')
  return res.json()
}

export async function triggerScan(): Promise<{
  scanned: boolean
  background?: boolean
  already_running?: boolean
  opportunities_count: number
}> {
  const res = await fetch(`${API_BASE}/scan`, { method: 'POST' })
  if (!res.ok) throw new Error('Skanowanie nie powiodło się')
  return res.json()
}

export async function fetchNotificationStatus(): Promise<NotificationStatus> {
  const res = await fetch(`${API_BASE}/notifications/status`)
  if (!res.ok) throw new Error('Nie udało się pobrać statusu powiadomień')
  return res.json()
}

export async function saveAlertSettings(settings: AlertSettings): Promise<AlertSettings> {
  const res = await fetch(`${API_BASE}/notifications/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
  if (!res.ok) throw new Error('Nie udało się zapisać ustawień')
  return res.json()
}

export async function saveTwilioConfig(config: TwilioConfig): Promise<{ saved: boolean }> {
  const res = await fetch(`${API_BASE}/notifications/twilio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || 'Nie udało się zapisać Twilio')
  }
  return res.json()
}

export async function testNotifications(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/notifications/test`, { method: 'POST' })
  if (!res.ok) throw new Error('Test powiadomień nie powiódł się')
  return res.json()
}

export async function fetchPaperPortfolio(): Promise<PaperPortfolio> {
  const res = await fetch(`${API_BASE}/paper/portfolio`)
  if (!res.ok) throw new Error('Nie udało się pobrać portfela')
  return res.json()
}

export async function fetchPaperMaxBuy(symbol: string): Promise<{ max_quantity: number }> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/paper/max-buy/${encoded}`)
  if (!res.ok) throw new Error('Brak danych')
  return res.json()
}

export async function placePaperOrder(order: PaperOrderRequest): Promise<unknown> {
  const res = await fetch(`${API_BASE}/paper/order`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = (err as { detail?: { message?: string } | string }).detail
    const msg = typeof detail === 'object' && detail?.message ? detail.message : String(detail || 'Transakcja nieudana')
    throw new Error(msg)
  }
  return res.json()
}

export async function resetPaperPortfolio(): Promise<PaperPortfolio> {
  const res = await fetch(`${API_BASE}/paper/reset`, { method: 'POST' })
  if (!res.ok) throw new Error('Reset nieudany')
  return res.json()
}

export async function fetchChart(symbol: string, range: ChartPreset = '3M'): Promise<ChartResponse> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/markets/chart/${encoded}?range=${range}`)
  if (!res.ok) throw new Error('Nie udało się pobrać wykresu')
  return res.json()
}

export async function fetchChartPresets(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/markets/chart-presets`)
  if (!res.ok) return CHART_PRESETS
  return res.json()
}
