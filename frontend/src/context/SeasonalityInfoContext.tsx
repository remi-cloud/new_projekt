import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export type SeasonalityInfoTarget =
  | { mode: 'instrument'; symbol: string }
  | { mode: 'month'; month: number; assetClass?: string | null }
  | null

type Ctx = {
  target: SeasonalityInfoTarget
  openInstrument: (symbol: string) => void
  openMonth: (month: number, assetClass?: string | null) => void
  close: () => void
}

const SeasonalityInfoContext = createContext<Ctx | null>(null)

export function SeasonalityInfoProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<SeasonalityInfoTarget>(null)
  const openInstrument = useCallback((symbol: string) => {
    setTarget({ mode: 'instrument', symbol })
  }, [])
  const openMonth = useCallback((month: number, assetClass?: string | null) => {
    setTarget({ mode: 'month', month, assetClass: assetClass ?? null })
  }, [])
  const close = useCallback(() => setTarget(null), [])
  const value = useMemo(
    () => ({ target, openInstrument, openMonth, close }),
    [target, openInstrument, openMonth, close],
  )
  return (
    <SeasonalityInfoContext.Provider value={value}>{children}</SeasonalityInfoContext.Provider>
  )
}

export function useSeasonalityInfo() {
  const ctx = useContext(SeasonalityInfoContext)
  if (!ctx) {
    // Safe no-op outside provider (e.g. embed) — avoid blank crash cards
    return {
      target: null,
      openInstrument: () => undefined,
      openMonth: () => undefined,
      close: () => undefined,
    } satisfies Ctx
  }
  return ctx
}
