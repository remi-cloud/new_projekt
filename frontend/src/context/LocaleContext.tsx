import { DATE_LOCALE, interpolate, LOCALES, translations, type Locale, type TranslationPath } from '../i18n'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { detectLocale, LOCALE_STORAGE_KEY } from '../i18n/utils'

interface LocaleContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (path: TranslationPath, vars?: Record<string, string | number>) => string
  tArray: (path: string) => string[]
  dateLocale: string
  weekdays: string[]
  months: string[]
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

function resolveValue(locale: Locale, path: string): unknown {
  let cur: unknown = translations[locale]
  for (const part of path.split('.')) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[part]
  }
  return cur
}

function resolveString(locale: Locale, path: string): string {
  const cur = resolveValue(locale, path)
  return typeof cur === 'string' ? cur : path
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale)

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    localStorage.setItem(LOCALE_STORAGE_KEY, next)
    document.documentElement.lang = next
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const t = useCallback(
    (path: TranslationPath, vars?: Record<string, string | number>) =>
      interpolate(resolveString(locale, path), vars),
    [locale],
  )

  const tArray = useCallback(
    (path: string): string[] => {
      const val = resolveValue(locale, path)
      return Array.isArray(val) && val.every((item) => typeof item === 'string') ? val : []
    },
    [locale],
  )

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
      tArray,
      dateLocale: DATE_LOCALE[locale],
      weekdays: [...translations[locale].macro.cal.weekdays],
      months: [...translations[locale].macro.cal.months],
    }),
    [locale, setLocale, t, tArray],
  )

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale() {
  const ctx = useContext(LocaleContext)
  if (!ctx) throw new Error('useLocale must be used within LocaleProvider')
  return ctx
}

export { LOCALES }
