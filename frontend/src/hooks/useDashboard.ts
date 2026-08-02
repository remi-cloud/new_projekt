import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchDashboard, triggerScan } from '../api'
import { DashboardResponse } from '../types'

async function fetchDashboardWithRetry(maxAttempts = 12): Promise<DashboardResponse> {
  let lastError: Error | null = null
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fetchDashboard()
    } catch (e) {
      lastError = e instanceof Error ? e : new Error('Błąd API')
      const msg = lastError.message.toLowerCase()
      const retryable = msg.includes('503') || msg.includes('skanowanie') || msg.includes('failed to fetch')
      if (!retryable || attempt === maxAttempts - 1) break
      await new Promise((r) => setTimeout(r, 2000))
    }
  }
  throw lastError ?? new Error('Nie udało się pobrać dashboardu')
}

export function useDashboard(pollMs = 60_000) {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [booting, setBooting] = useState(false)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  const load = useCallback(async (withRetry = false) => {
    try {
      if (withRetry) setBooting(true)
      const dashboard = withRetry
        ? await fetchDashboardWithRetry()
        : await fetchDashboard()
      if (!alive.current) return
      setData(dashboard)
      setError(null)
      setBooting(false)
    } catch (e) {
      if (!alive.current) return
      setError(e instanceof Error ? e.message : 'Błąd połączenia z API')
      setBooting(false)
    } finally {
      if (alive.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(true)
    const interval = setInterval(() => load(false), pollMs)
    return () => clearInterval(interval)
  }, [load, pollMs])

  const scan = async () => {
    setScanning(true)
    try {
      await triggerScan()
      await load(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Skanowanie nie powiodło się')
    } finally {
      setScanning(false)
    }
  }

  return { data, loading, scanning, error, booting, load: () => load(true), scan }
}
