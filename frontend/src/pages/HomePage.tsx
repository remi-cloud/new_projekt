import { useNavigate } from 'react-router-dom'
import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { ErrorState } from '../components/Loading'
import { OpportunityCard } from '../components/OpportunityCard'
import { MarketSummaryBanner } from '../components/MarketAssessmentCard'
import { SIGNAL_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'

export function HomePage() {
  const { data, error, reload } = useDashboardContext()
  const navigate = useNavigate()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  const topOpps = data.opportunities.slice(0, 3)

  return (
    <div className="home-page">
      {data.market_summary && <MarketSummaryBanner summary={data.market_summary} />}

      <section className="hero">
        <p className="hero-eyebrow">Globalne rynki · 24/7</p>
        <h1>Handluj zgodnie z <span>rytmami rynku</span></h1>
        <p className="hero-desc">
          {data.market_summary?.total_assets ?? 0} instrumentów na świecie — krypto, indeksy, akcje,
          obligacje, surowce i forex. Ocena cykliczna każdego produktu.
        </p>
        <div className="hero-actions">
          <button type="button" className="btn btn-primary btn-lg tap-target" onClick={() => navigate('/dashboard')}>
            Otwórz panel
          </button>
          <button type="button" className="btn btn-ghost tap-target" onClick={() => navigate('/rynki')}>
            Rynki globalne ({data.market_summary?.total_assets ?? 0})
          </button>
        </div>
        <div className="hero-stats">
          <div className="hero-stat">
            <div className="hero-stat-value">{data.market_summary?.total_assets ?? 0}</div>
            <div className="hero-stat-label">Instrumentów</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">{data.opportunities.length}</div>
            <div className="hero-stat-label">Sygnałów</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">{SIGNAL_LABELS[data.bitcoin_cycle.signal]}</div>
            <div className="hero-stat-label">BTC</div>
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
            <h2 className="section-title">Top okazje</h2>
            <button type="button" className="link-btn tap-target" onClick={() => navigate('/okazje')}>
              Wszystkie →
            </button>
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
