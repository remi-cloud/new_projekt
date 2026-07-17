import { createContext, useContext, ReactNode, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import type { HealthResponse } from '../api'
import { useDashboard } from '../hooks/useDashboard'
import { usePaperPortfolioFeed } from '../hooks/usePaperPortfolio'
import { useSystemHealth } from '../hooks/useSystemHealth'
import { DashboardResponse, PaperPortfolio } from '../types'
import { needsDashboardFeed, needsLiveSse, needsPortfolioFeed } from '../utils/routeActivity'

interface DashboardContextValue {
  data: DashboardResponse | null
  loading: boolean
  scanning: boolean
  error: string | null
  liveConnected: boolean
  lastEventAt: string | null
  health: HealthResponse | null
  reload: () => Promise<void>
  scan: () => Promise<void>
  portfolio: PaperPortfolio | null
  portfolioLoading: boolean
  portfolioError: string | null
  reloadPortfolio: () => Promise<void>
  dashboardActive: boolean
}

const DashboardContext = createContext<DashboardContextValue | null>(null)

export function DashboardProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const dashboardActive = needsDashboardFeed(pathname)
  const portfolioActive = needsPortfolioFeed(pathname)
  const sseActive = needsLiveSse(pathname)

  const { health } = useSystemHealth(true)
  const dashboard = useDashboard({
    enabled: dashboardActive,
    poll: dashboardActive,
    sse: sseActive,
  })
  const portfolioFeed = usePaperPortfolioFeed(
    60_000,
    sseActive ? dashboard.lastEventAt : null,
    portfolioActive,
  )

  const value = useMemo<DashboardContextValue>(
    () => ({
      ...dashboard,
      ...portfolioFeed,
      health,
      dashboardActive,
    }),
    [dashboard, portfolioFeed, health, dashboardActive],
  )

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

export function useDashboardContext() {
  const ctx = useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboardContext must be used within DashboardProvider')
  return ctx
}

/** Portfolio state from global feed (polls only on trading routes). */
export function usePaperPortfolio() {
  const ctx = useDashboardContext()
  return {
    portfolio: ctx.portfolio,
    loading: ctx.portfolioLoading,
    error: ctx.portfolioError,
    reload: ctx.reloadPortfolio,
  }
}
