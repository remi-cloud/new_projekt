import { useCallback, useEffect, useState } from 'react'
import { fetchQuote } from '../api'
import { LiveQuote } from '../types'
import { useDashboardContext } from '../context/DashboardContext'

/** Fresh price from Yahoo quote API — independent of chart cache. */
export function useLiveQuote(symbol: string, enabled: boolean, pollMs = 15_000) {
  const { lastEventAt } = useDashboardContext()
  const [quote, setQuote] = useState<LiveQuote | null>(null)

  const reload = useCallback(async () => {
    try {
      const data = await fetchQuote(symbol)
      setQuote(data)
    } catch {
      /* fallback: chart price via parent */
    }
  }, [symbol])

  useEffect(() => {
    if (!enabled) return
    reload()
    const id = setInterval(reload, pollMs)
    return () => clearInterval(id)
  }, [enabled, reload, pollMs])

  useEffect(() => {
    if (enabled && lastEventAt) reload()
  }, [enabled, lastEventAt, reload])

  return quote
}
