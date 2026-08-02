import { Link } from 'react-router-dom'
import { CycleCardAlpha, CycleCardBeta } from '../components/CycleCards'
import LoadingState, { ErrorState } from '../components/LoadingState'
import OpportunityCard from '../components/OpportunityCard'
import AssetsTable from '../components/AssetsTable'
import { useDashboard } from '../hooks/useDashboard'

export default function DashboardPage() {
  const { data, loading, scanning, error, load, scan } = useDashboard()

  if (loading) return <LoadingState message="Ładowanie danych rynkowych…" />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="page-lead">Modele, okazje i notowania w jednym widoku.</p>
        </div>
        <div className="page-actions">
          <div className="status-badge">
            <span className={`status-dot ${data.scanner_running ? '' : 'offline'}`} />
            Skaner {data.scanner_running ? 'aktywny' : 'offline'}
          </div>
          {data.last_scan_at && (
            <span className="meta-time">
              Ostatni skan: {new Date(data.last_scan_at).toLocaleString('pl-PL')}
            </span>
          )}
          <button className="btn btn-primary" onClick={scan} disabled={scanning} type="button">
            {scanning ? 'Skanowanie…' : 'Skanuj teraz'}
          </button>
        </div>
      </div>

      {error && <p className="inline-error">{error}</p>}

      <div className="cycles-grid">
        <CycleCardAlpha model={data.alpha_model} />
        <CycleCardBeta model={data.beta_model} />
      </div>

      <h2 className="section-title">
        Top okazje
        <span className="count">{Math.min(6, data.opportunities.length)}</span>
        <Link to="/okazje" className="section-link">
          Wszystkie okazje →
        </Link>
        <Link to="/superokazje" className="section-link">
          Superokazje →
        </Link>
      </h2>
      {data.opportunities.length === 0 ? (
        <p className="empty">Brak aktywnych sygnałów — modele nie wskazują na wyraźne okazje.</p>
      ) : (
        <div className="opportunities-grid">
          {data.opportunities.slice(0, 6).map((opp) => (
            <OpportunityCard key={`${opp.symbol}-${opp.created_at}`} opp={opp} />
          ))}
        </div>
      )}

      <h2 className="section-title">
        Notowania
        <span className="count">{data.monitored_assets.length}</span>
        <Link to="/rynki" className="section-link">
          Wszystkie rynki →
        </Link>
      </h2>
      <AssetsTable assets={data.monitored_assets.slice(0, 12)} />
    </div>
  )
}
