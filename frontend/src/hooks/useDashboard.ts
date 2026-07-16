import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchDashboard, triggerScan } from '../api'
import { resolveApiMessage } from '../i18n/utils'
import { useLiveFeed } from './useLiveFeed'
import { DashboardResponse } from '../types'
import { getAutoRefreshIntervalMs, isAutoRefreshEnabled } from '../components/AutoRefreshToggle'

type UseDashboardOptions = {
  /** Fetch dashboard JSON (scanner data). */
  enabled?: boolean
  /** Poll on an interval while enabled. */
  poll?: boolean
  /** Subscribe to /api/live/stream SSE. */
  sse?: boolean
}

export function useDashboard(options: UseDashboardOptions = {}) {
  const { enabled = true, poll = enabled, sse = enabled } = options
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const reloadTimer = useRef<number | null>(null)
  const [tickMs, setTickMs] = useState(() => getAutoRefreshIntervalMs())

  const load = useCallback(async () => {
    if (!enabled) return
    try {
      const dashboard = await fetchDashboard()
      setData(dashboard)
      setError(null)
    } catch {
      setError(resolveApiMessage('noConnection'))
    } finally {
      setLoading(false)
    }
  }, [enabled])

  const scheduleReload = useCallback(() => {
    if (!enabled) return
    if (reloadTimer.current != null) window.clearTimeout(reloadTimer.current)
    reloadTimer.current = window.setTimeout(() => {
      reloadTimer.current = null
      void load()
    }, 750)
  }, [enabled, load])

  useEffect(() => {
    const sync = () => setTickMs(getAutoRefreshIntervalMs())
    sync()
    window.addEventListener('cyclical-auto-refresh', sync)
    return () => window.removeEventListener('cyclical-auto-refresh', sync)
  }, [])

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }
    setLoading((prev) => (data ? false : prev || true))
    void load()
  }, [enabled, load])

  useEffect(() => {
    if (!enabled || !poll) return
    if (!isAutoRefreshEnabled()) {
      const interval = setInterval(() => void load(), 60_000)
      return () => clearInterval(interval)
    }
    const interval = setInterval(() => void load(), tickMs)
    return () => clearInterval(interval)
  }, [enabled, poll, load, tickMs])

  useEffect(
    () => () => {
      if (reloadTimer.current != null) window.clearTimeout(reloadTimer.current)
    },
    [],
  )

  const { connected: liveConnected, lastEventAt } = useLiveFeed(
    (event) => {
      if (event.type === 'price_tick' || event.type === 'full_scan' || event.type === 'alerts') {
        scheduleReload()
      }
    },
    sse,
  )

  const scan = useCallback(async () => {
    if (!enabled) return
    setScanning(true)
    try {
      const result = await triggerScan()
      await load()
      if (result.already_running) return
      void (async () => {
        for (let i = 0; i < 40; i++) {
          await new Promise((r) => setTimeout(r, 3000))
          try {
            const dashboard = await fetchDashboard()
            setData(dashboard)
            if (!dashboard.scan_in_progress) break
          } catch {
            break
          }
        }
      })()
    } catch {
      setError(resolveApiMessage('scanFailed'))
      throw new Error('scan failed')
    } finally {
      setScanning(false)
    }
  }, [enabled, load])

  return { data, loading, scanning, error, reload: load, scan, liveConnected, lastEventAt }
}
