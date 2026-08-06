import { useLocale } from '../context/LocaleContext'
import { resolveApiMessage } from '../i18n/utils'
import type { ApiErrorCode } from '../i18n/apiErrors'
import { en } from '../i18n/locales/en'

export function Loading({ message }: { message?: string }) {
  const { t } = useLocale()

  return (
    <div className="loading">
      <div className="spinner" />
      <p>{message ?? t('common.loadingMarket')}</p>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t, locale } = useLocale()
  const display =
    message in en.api ? resolveApiMessage(message as ApiErrorCode, locale) : message

  return (
    <div className="error">
      <p>{display}</p>
      <button className="btn btn-primary" onClick={onRetry}>
        {t('common.retry')}
      </button>
    </div>
  )
}
