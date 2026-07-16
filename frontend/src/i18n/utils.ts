import type { Locale } from './types'
import type { ApiErrorCode } from './apiErrors'
import { isApiError } from './apiErrors'
import { pl } from './locales/pl'
import { de } from './locales/de'
import { en } from './locales/en'
import { fil } from './locales/fil'
import { es } from './locales/es'
import { fr } from './locales/fr'
import { it } from './locales/it'

export const LOCALE_STORAGE_KEY = 'cyclical-locale'

const localeBundles = { pl, de, en, fil, es, fr, it }

export const DATE_LOCALE: Record<Locale, string> = {
  pl: 'pl-PL',
  de: 'de-DE',
  en: 'en-US',
  fil: 'fil-PH',
  es: 'es-ES',
  fr: 'fr-FR',
  it: 'it-IT',
}

export function interpolate(str: string, vars?: Record<string, string | number>): string {
  if (!vars) return str
  return str.replace(/\{\{(\w+)\}\}/g, (_, key: string) => String(vars[key] ?? ''))
}

export function detectLocale(): Locale {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY) as Locale | null
  if (stored && DATE_LOCALE[stored]) return stored
  const browser = navigator.language.slice(0, 2)
  const map: Record<string, Locale> = {
    pl: 'pl', de: 'de', en: 'en', fil: 'fil', tl: 'fil',
    es: 'es', fr: 'fr', it: 'it',
  }
  return map[browser] ?? 'pl'
}

export function resolveApiMessage(code: ApiErrorCode, locale?: Locale): string {
  const loc = locale ?? detectLocale()
  const bundle = localeBundles[loc] ?? en
  return bundle.api[code] ?? en.api[code] ?? code
}

/** Turn thrown ApiError / Error into a localized user-facing string. */
export function formatThrownError(err: unknown, fallback: string, locale?: Locale): string {
  if (isApiError(err)) return resolveApiMessage(err.code, locale)
  if (err instanceof Error && err.message in en.api) {
    return resolveApiMessage(err.message as ApiErrorCode, locale)
  }
  if (err instanceof Error && err.message) return err.message
  return fallback
}
