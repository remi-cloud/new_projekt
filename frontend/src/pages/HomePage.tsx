import { Link } from 'react-router-dom'
import { CycleCardBitcoin, CycleCardPresidential } from '../components/CycleCards'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { useDashboard } from '../hooks/useDashboard'

export default function HomePage() {
  const { data, loading, error, load } = useDashboard()

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-atmosphere" aria-hidden />
        <div className="hero-content">
          <p className="hero-brand">Cyclical Trader</p>
          <h1 className="hero-title">Skanuj rynek. Łap cykl. Działaj.</h1>
          <p className="hero-lead">
            Monitor 24/7 okazji kupna i sprzedaży opartych na cyklu Bitcoina oraz cyklu
            prezydenckim USA — bez skalpingu, bez HFT.
          </p>
          <div className="hero-cta">
            <Link className="btn btn-primary" to="/dashboard">
              Otwórz dashboard
            </Link>
            <Link className="btn btn-ghost" to="/okazje">
              Zobacz okazje
            </Link>
          </div>
        </div>
      </section>

      {loading && <LoadingState message="Pobieranie statusu cykli…" />}
      {error && !data && <ErrorState message={error} onRetry={load} />}
      {data && (
        <section className="home-cycles">
          <h2 className="section-title">Gdzie jesteśmy w cyklu</h2>
          <div className="cycles-grid">
            <CycleCardBitcoin cycle={data.bitcoin_cycle} />
            <CycleCardPresidential cycle={data.presidential_cycle} />
          </div>
          <div className="home-stats">
            <div className="home-stat">
              <strong>{data.opportunities.length}</strong>
              <span>aktywnych sygnałów</span>
            </div>
            <div className="home-stat">
              <strong>{data.monitored_assets.length}</strong>
              <span>monitorowanych instrumentów</span>
            </div>
            <div className="home-stat">
              <strong>{data.scanner_running ? 'ON' : 'OFF'}</strong>
              <span>skaner 24/7</span>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
