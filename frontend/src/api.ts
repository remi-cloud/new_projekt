import { AlertSettings, DashboardResponse, NotificationStatus, TwilioConfig } from './types'
import { ChartPreset, ChartResponse } from './types/chart'

export const API_BASE = '/api'

export async function fetchDashboard(): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/dashboard`)
  if (!res.ok) throw new Error('Nie udało się pobrać danych dashboardu')
  return res.json()
}

export async function triggerScan(): Promise<{ scanned: boolean; opportunities_count: number }> {
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

export async function fetchChart(symbol: string, range: ChartPreset = '3M'): Promise<ChartResponse> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/markets/chart/${encoded}?range=${range}`)
  if (!res.ok) throw new Error('Nie udało się pobrać wykresu')
  return res.json()
}

export const CHART_PRESETS: ChartPreset[] = ['1D', '1W', '1M', '3M', '1Y', 'MAX']
