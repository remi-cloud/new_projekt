import { useCallback, useEffect, useState } from 'react'
import { fetchDashboard, triggerScan } from '../api'
import { useLiveFeed } from './useLiveFeed'
import { DashboardResponse } from '../types'

export function useDashboard(pollMs = 30_000) {
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

  const { connected: liveConnected, lastEventAt } = useLiveFeed((event) => {
    if (event.type === 'price_tick' || event.type === 'full_scan' || event.type === 'alerts') {
      load()
    }
  })

  const scan = useCallback(async () => {
    setScanning(true)
    try {
      await triggerScan()
      await load()
    } catch {
      setError('Skanowanie nie powiodło się')
      throw new Error('scan failed')
    } finally {
      setScanning(false)
    }
  }, [load])

  return { data, loading, scanning, error, reload: load, scan, liveConnected, lastEventAt }
}
