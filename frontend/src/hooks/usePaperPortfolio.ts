import { useCallback, useEffect, useState } from 'react'
import { fetchPaperPortfolio } from '../api'
import { resolveApiMessage } from '../i18n/utils'
import { PaperPortfolio } from '../types'

/** Portfolio feed — polls only on routes that show paper trading. */
export function usePaperPortfolioFeed(
  pollMs = 60_000,
  lastEventAt: string | null = null,
  enabled = true,
) {
  const [portfolio, setPortfolio] = useState<PaperPortfolio | null>(null)
  const [portfolioLoading, setPortfolioLoading] = useState(enabled)
  const [portfolioError, setPortfolioError] = useState<string | null>(null)

  const reloadPortfolio = useCallback(async () => {
    if (!enabled) return
    try {
      const data = await fetchPaperPortfolio()
      setPortfolio(data)
      setPortfolioError(null)
    } catch {
      setPortfolioError(resolveApiMessage('loadPortfolio'))
    } finally {
      setPortfolioLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    if (!enabled) {
      setPortfolioLoading(false)
      return
    }
    void reloadPortfolio()
    const t = setInterval(() => void reloadPortfolio(), pollMs)
    return () => clearInterval(t)
  }, [enabled, reloadPortfolio, pollMs])

  useEffect(() => {
    if (enabled && lastEventAt) void reloadPortfolio()
  }, [enabled, lastEventAt, reloadPortfolio])

  return { portfolio, portfolioLoading, portfolioError, reloadPortfolio }
}
