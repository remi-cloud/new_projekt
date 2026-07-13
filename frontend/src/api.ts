import { ChartPreset, ChartResponse } from './types/chart'
import { DashboardResponse } from './types'

const API_BASE = '/api'

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

export async function fetchChart(symbol: string, range: ChartPreset = '3M'): Promise<ChartResponse> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/markets/chart/${encoded}?range=${range}`)
  if (!res.ok) throw new Error('Nie udało się pobrać wykresu')
  return res.json()
}

export const CHART_PRESETS: ChartPreset[] = ['1D', '1W', '1M', '3M', '1Y', 'MAX']
