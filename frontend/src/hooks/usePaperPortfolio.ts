import { useCallback, useEffect, useState } from 'react'
import { fetchPaperPortfolio } from '../api'
import { PaperPortfolio } from '../types'

/** Global portfolio feed — polls while app is open, reacts to live price ticks. */
export function usePaperPortfolioFeed(pollMs = 60_000, lastEventAt: string | null = null) {
  const [portfolio, setPortfolio] = useState<PaperPortfolio | null>(null)
  const [portfolioLoading, setPortfolioLoading] = useState(true)
  const [portfolioError, setPortfolioError] = useState<string | null>(null)

  const reloadPortfolio = useCallback(async () => {
    try {
      const data = await fetchPaperPortfolio()
      setPortfolio(data)
      setPortfolioError(null)
    } catch {
      setPortfolioError('Nie udało się załadować portfela')
    } finally {
      setPortfolioLoading(false)
    }
  }, [])

  useEffect(() => {
    reloadPortfolio()
    const t = setInterval(reloadPortfolio, pollMs)
    return () => clearInterval(t)
  }, [reloadPortfolio, pollMs])

  useEffect(() => {
    if (lastEventAt) reloadPortfolio()
  }, [lastEventAt, reloadPortfolio])

  return { portfolio, portfolioLoading, portfolioError, reloadPortfolio }
}
