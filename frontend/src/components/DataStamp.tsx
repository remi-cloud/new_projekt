import { useLocale } from '../context/LocaleContext'

/** "Źródło: X · aktualizacja: <czas>" — every live number on a card names its origin. */
export function formatStamp(iso: string | null | undefined, dateLocale: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(dateLocale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function DataStamp({
  source,
  updatedAt,
  stale,
  className = '',
}: {
  source?: string | null
  updatedAt?: string | null
  stale?: boolean
  className?: string
}) {
  const { t, dateLocale } = useLocale()
  const when = formatStamp(updatedAt, dateLocale)
  return (
    <p className={`data-stamp ${stale ? 'data-stamp-stale' : ''} ${className}`.trim()} data-testid="data-stamp">
      {source ? (
        <span>
          {t('liveData.source')}: {source}
        </span>
      ) : null}
      {source ? ' · ' : null}
      <span>
        {stale ? `${t('liveData.stale')} — ${t('liveData.lastReal')}` : t('liveData.updated')}:{' '}
        {when || t('liveData.noData')}
      </span>
    </p>
  )
}
