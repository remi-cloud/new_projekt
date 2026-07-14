import { useNavigate } from 'react-router-dom'
import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { MarketSummaryBanner } from '../components/MarketAssessmentCard'
import { OpportunityCard } from '../components/OpportunityCard'
import { ErrorState } from '../components/Loading'
import { SIGNAL_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'

export function DashboardPage() {
  const { data, error, reload } = useDashboardContext()
  const navigate = useNavigate()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  const momentumPicks = data.opportunities.filter((o) => o.is_momentum_pick)

  return (
    <div className="dashboard-page">
      {data.market_summary && (
        <section className="dashboard-section dashboard-summary">
          <MarketSummaryBanner summary={data.market_summary} />
        </section>
      )}

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Cykle rynkowe</h2>
        </div>
        <div className="cycles-grid">
          <CycleCardBitcoin cycle={data.bitcoin_cycle} />
          <CycleCardPresidential cycle={data.presidential_cycle} />
        </div>
      </section>

      <div className="dashboard-columns">
        <section className="dashboard-section dashboard-section-main">
          <div className="section-header">
            <h2 className="section-title">
              Okazje tradingowe
              <span className="count">{data.opportunities.length}</span>
            </h2>
            <button type="button" className="link-btn tap-target" onClick={() => navigate('/okazje')}>
              Wszystkie →
            </button>
          </div>
          {data.opportunities.length === 0 ? (
            <p className="empty-state">Brak aktywnych sygnałów.</p>
          ) : (
            <div className="opportunities-grid">
              {data.opportunities.slice(0, 6).map((opp) => (
                <OpportunityCard key={`${opp.symbol}-${opp.created_at}`} opp={opp} />
              ))}
            </div>
          )}
        </section>

        <aside className="dashboard-section dashboard-section-side">
          {momentumPicks.length > 0 && (
            <div className="side-panel momentum-panel">
              <h3 className="side-panel-title">⚡ Momentum + cykl</h3>
              <p className="side-panel-desc">Sygnały gdzie momentum i cykle się zgadzają</p>
              <div className="momentum-list">
                {momentumPicks.slice(0, 5).map((opp) => (
                  <button
                    key={`mom-${opp.symbol}`}
                    type="button"
                    className="momentum-item tap-target"
                    onClick={() => navigate(`/instrument/${encodeURIComponent(opp.symbol)}`)}
                  >
                    <div className="momentum-item-top">
                      <span className="momentum-item-name">{opp.name}</span>
                      <span className={`signal-tag signal-${opp.action}`}>{SIGNAL_LABELS[opp.action]}</span>
                    </div>
                    <div className="momentum-item-meta">
                      {opp.momentum_score != null && <span>Mom. {opp.momentum_score.toFixed(0)}</span>}
                      <span>{opp.confidence}% pewności</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="side-panel">
            <h3 className="side-panel-title">Top rynki wg oceny</h3>
            <div className="markets-list markets-list-compact">
              {(data.market_assessments ?? []).slice(0, 5).map((item) => (
                <button
                  key={item.symbol}
                  type="button"
                  className="market-card market-card-clickable tap-target"
                  onClick={() => navigate(`/instrument/${encodeURIComponent(item.symbol)}`)}
                >
                  <div className="market-card-top">
                    <div>
                      <div className="market-name">{item.name}</div>
                      <div className="market-symbol">{item.symbol}</div>
                    </div>
                    <span className={`signal-tag signal-${item.signal}`}>{SIGNAL_LABELS[item.signal]}</span>
                  </div>
                  {item.momentum_score != null && (
                    <div className="market-momentum">Momentum: {item.momentum_score.toFixed(0)}</div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
