import { Link } from 'react-router-dom'
import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { ErrorState } from '../components/Loading'
import { OpportunityCard } from '../components/OpportunityCard'
import { SIGNAL_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'

export function HomePage() {
  const { data, error, reload } = useDashboardContext()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  const topOpps = data.opportunities.slice(0, 3)

  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero-content">
          <p className="hero-eyebrow">Trading cykliczny · 24/7</p>
          <h1>Handluj zgodnie z <span>rytmami rynku</span></h1>
          <p className="hero-desc">
            Nie skalping. Nie HFT. Aplikacja śledzi cykl Bitcoin (364 dni spadków + 1064 dni wzrostu)
            dla krypto oraz cykl prezydencki USA dla akcji, obligacji, surowców i forex.
          </p>
          <div className="hero-actions">
            <Link to="/dashboard" className="btn btn-primary btn-lg">Otwórz panel</Link>
            <Link to="/okazje" className="btn btn-ghost">Okazje ({data.opportunities.length})</Link>
          </div>
        </div>
        <div className="hero-stats">
          <div className="hero-stat">
            <div className="hero-stat-value">{data.monitored_assets.length}</div>
            <div className="hero-stat-label">Instrumentów</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">{data.opportunities.length}</div>
            <div className="hero-stat-label">Aktywnych sygnałów</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">{SIGNAL_LABELS[data.bitcoin_cycle.signal]}</div>
            <div className="hero-stat-label">Sygnał BTC</div>
          </div>
        </div>
      </section>

      <section className="home-cycles">
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </section>

      {topOpps.length > 0 && (
        <section>
          <div className="section-header">
            <h2 className="section-title">Najlepsze okazje teraz</h2>
            <Link to="/okazje" className="link-more">Wszystkie →</Link>
          </div>
          <div className="opportunities-grid">
            {topOpps.map((opp) => (
              <OpportunityCard key={`${opp.symbol}-${opp.created_at}`} opp={opp} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
