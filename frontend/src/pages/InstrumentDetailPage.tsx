import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { InstrumentPanel } from '../components/InstrumentPanel'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'

export function InstrumentDetailPage() {
  const { symbol: encoded } = useParams()
  const symbol = encoded ? decodeURIComponent(encoded) : ''
  const navigate = useNavigate()
  const { data, error, reload } = useDashboardContext()

  const item = useMemo(
    () => data?.market_assessments.find((a) => a.symbol === symbol),
    [data, symbol],
  )

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return <Loading />
  if (!item) {
    return (
      <div className="empty-state">
        <p>Instrument nie znaleziony: {symbol}</p>
        <button type="button" className="btn btn-primary tap-target" onClick={() => navigate('/rynki')}>
          Wróć do rynków
        </button>
      </div>
    )
  }

  return (
    <div className="instrument-detail institutional-page">
      <header className="detail-header">
        <button type="button" className="back-btn tap-target" onClick={() => navigate(-1)}>
          ← Rynki
        </button>
        <div className="detail-header-meta">
          <span className="detail-eyebrow">Instrument · Analiza cykliczna</span>
          <h1 className="detail-title">{item.symbol}</h1>
          <p className="detail-subtitle">{item.name}</p>
        </div>
      </header>
      <InstrumentPanel item={item} expanded />
    </div>
  )
}
