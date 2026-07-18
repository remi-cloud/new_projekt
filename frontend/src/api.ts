import { DashboardResponse, HistoryResponse } from './types'

const API_BASE = '/api'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`Błąd API (${res.status})`)
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
  const res = await fetch(`${API_BASE}/scan`, { method: 'POST' })
  if (!res.ok) throw new Error('Skanowanie nie powiodło się')
  return res.json()
}

export async function fetchHistory(): Promise<HistoryResponse> {
  return getJson<HistoryResponse>('/history')
}
