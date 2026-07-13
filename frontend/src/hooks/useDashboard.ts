import { useCallback, useEffect, useState } from 'react'
import { fetchDashboard, triggerScan } from '../api'
import { DashboardResponse } from '../types'

export function useDashboard(pollMs = 90_000) {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const dashboard = await fetchDashboard()
      setData(dashboard)
      setError(null)
    } catch {
      setError('Brak połączenia — sprawdź internet')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, pollMs)
    return () => clearInterval(interval)
  }, [load, pollMs])

  const scan = async () => {
    setScanning(true)
    try {
      await triggerScan()
      await load()
    } catch {
      setError('Skanowanie nie powiodło się')
    } finally {
      setScanning(false)
    }
  }

  return { data, loading, scanning, error, reload: load, scan }
}
