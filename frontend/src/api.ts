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
