import type { Locale } from './types'

export type ApiErrorCode =
  | 'fetchDashboard'
  | 'scanFailed'
  | 'fetchNotifications'
  | 'saveSettings'
  | 'saveTwilio'
  | 'testNotifications'
  | 'fetchPortfolio'
  | 'noData'
  | 'tradeFailed'
  | 'resetFailed'
  | 'fetchPosition'
  | 'cancelOrder'
  | 'cancelAllOrders'
  | 'closePosition'
  | 'fetchPrice'
  | 'fetchChart'
  | 'fetchCalendar'
  | 'fetchNews'
  | 'refreshNews'
  | 'fetchAiStatus'
  | 'aiChatFailed'
  | 'aiFeedbackFailed'
  | 'aiHistoryFailed'
  | 'aiAnalyzeFailed'
  | 'noConnection'
  | 'loadPortfolio'
  | 'pushUnsupported'
  | 'pushDenied'
  | 'pushSubscribeFailed'
  | 'rateLimited'
  | 'badRequest'
  | 'serverUnavailable'
  | 'roiAssetsFailed'
  | 'roiCalculateFailed'
  | 'roiShowcaseFailed'
  | 'fetchLiveFailed'
  | 'fetchGrowthFailed'
  | 'newsletterFailed'
  | 'contactFailed'
  | 'embedFailed'

export class ApiError extends Error {
  readonly code: ApiErrorCode

  constructor(code: ApiErrorCode) {
    super(code)
    this.name = 'ApiError'
    this.code = code
  }
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError
}

export function apiErrorMessage(code: ApiErrorCode, t: (path: `api.${ApiErrorCode}`) => string): string {
  return t(`api.${code}`)
}

export const TV_LOCALE: Record<Locale, string> = {
  pl: 'pl',
  de: 'de',
  en: 'en',
  fil: 'en',
  es: 'es',
  fr: 'fr',
  it: 'it',
}
