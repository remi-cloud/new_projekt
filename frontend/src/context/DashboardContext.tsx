import { createContext, useContext, ReactNode } from 'react'
import { useDashboard } from '../hooks/useDashboard'
import { usePaperPortfolioFeed } from '../hooks/usePaperPortfolio'
import { DashboardResponse, PaperPortfolio } from '../types'

interface DashboardContextValue {
  data: DashboardResponse | null
  loading: boolean
  scanning: boolean
  error: string | null
  liveConnected: boolean
  lastEventAt: string | null
  reload: () => Promise<void>
  scan: () => Promise<void>
  portfolio: PaperPortfolio | null
  portfolioLoading: boolean
  portfolioError: string | null
  reloadPortfolio: () => Promise<void>
}

const DashboardContext = createContext<DashboardContextValue | null>(null)

export function DashboardProvider({ children }: { children: ReactNode }) {
  const dashboard = useDashboard()
  const portfolioFeed = usePaperPortfolioFeed(60_000, dashboard.lastEventAt)
  const value: DashboardContextValue = { ...dashboard, ...portfolioFeed }

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

export function useDashboardContext() {
  const ctx = useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboardContext must be used within DashboardProvider')
  return ctx
}

/** Portfolio state from global feed (polls in background on all pages). */
export function usePaperPortfolio() {
  const ctx = useDashboardContext()
  return {
    portfolio: ctx.portfolio,
    loading: ctx.portfolioLoading,
    error: ctx.portfolioError,
    reload: ctx.reloadPortfolio,
  }
}
