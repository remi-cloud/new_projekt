import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchMarketAssessment } from '../api'
import { BrokerPurchaseHint } from '../components/BrokerPurchaseHint'
import { InstrumentPanel } from '../components/InstrumentPanel'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import type { AssetCycleAssessment } from '../types'

export function InstrumentDetailPage() {
  const { symbol: encoded } = useParams()
  const symbol = encoded ? decodeURIComponent(encoded) : ''
  const navigate = useNavigate()
  const { t } = useLocale()
  const { data, error, reload, loading } = useDashboardContext()
  const [item, setItem] = useState<AssetCycleAssessment | null>(null)
  const [itemLoading, setItemLoading] = useState(true)
  const [itemError, setItemError] = useState<string | null>(null)

  const cached = useMemo(
    () => data?.market_assessments.find((a) => a.symbol === symbol) ?? null,
    [data, symbol],
  )

  useEffect(() => {
    if (!symbol) return
    if (cached) {
      setItem(cached)
      setItemLoading(false)
      setItemError(null)
      return
    }

    let cancelled = false
    setItemLoading(true)
    setItemError(null)
    void fetchMarketAssessment(symbol)
      .then((assessment) => {
        if (!cancelled) {
          setItem(assessment)
          setItemError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setItem(null)
          setItemError(formatThrownError(err, t('instrument.notFound', { symbol })))
        }
      })
      .finally(() => {
        if (!cancelled) setItemLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [symbol, cached, t])

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if ((loading && !data) || itemLoading) return <Loading message={t('layout.loading')} />

  if (itemError || !item) {
    return (
      <div className="empty-state">
        <p>{itemError ?? t('instrument.notFound', { symbol })}</p>
        <button type="button" className="btn btn-primary tap-target" onClick={() => navigate('/rynki')}>
          {t('instrument.backToMarkets')}
        </button>
      </div>
    )
  }

  const limited = item.confidence === 0

  return (
    <div className="instrument-detail institutional-page">
      <header className="detail-header">
        <button type="button" className="back-btn tap-target" onClick={() => navigate(-1)}>
          {t('instrument.backMarkets')}
        </button>
        <div className="detail-header-meta">
          <span className="detail-eyebrow">{t('instrument.eyebrow')}</span>
          <h1 className="detail-title">{item.symbol}</h1>
          <p className="detail-subtitle">{item.name}</p>
          {limited && <p className="detail-limited-hint">{t('instrument.limitedData')}</p>}
        </div>
      </header>
      <BrokerPurchaseHint info={item.broker_info} />
      <InstrumentPanel item={item} expanded />
    </div>
  )
}
