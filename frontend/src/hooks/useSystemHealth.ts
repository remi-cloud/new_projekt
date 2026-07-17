import { useCallback, useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '../api'

/** Lightweight /api/health poll — keeps header status accurate on all routes. */
export function useSystemHealth(enabled = true, intervalMs = 30_000) {
  const [health, setHealth] = useState<HealthResponse | null>(null)

  const load = useCallback(async () => {
    try {
      setHealth(await fetchHealth())
    } catch {
      setHealth(null)
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      setHealth(null)
      return
    }
    void load()
    const id = window.setInterval(() => void load(), intervalMs)
    return () => window.clearInterval(id)
  }, [enabled, intervalMs, load])

  return { health, reload: load }
}
