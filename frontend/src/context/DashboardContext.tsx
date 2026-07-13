import { createContext, useContext, ReactNode } from 'react'
import { useDashboard } from '../hooks/useDashboard'
import { DashboardResponse } from '../types'

interface DashboardContextValue {
  data: DashboardResponse | null
  loading: boolean
  scanning: boolean
  error: string | null
  reload: () => Promise<void>
  scan: () => Promise<void>
}

const DashboardContext = createContext<DashboardContextValue | null>(null)

export function DashboardProvider({ children }: { children: ReactNode }) {
  const value = useDashboard()
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

export function useDashboardContext() {
  const ctx = useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboardContext must be used within DashboardProvider')
  return ctx
}
