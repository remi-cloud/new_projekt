import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { MarketSummaryBanner } from '../components/MarketAssessmentCard'
import { OpportunityCard } from '../components/OpportunityCard'
import { ErrorState } from '../components/Loading'
import { SIGNAL_LABELS } from '../constants'
import { useDashboardContext } from '../context/DashboardContext'

export function DashboardPage() {
  const { data, error, reload } = useDashboardContext()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  return (
    <>
      {data.market_summary && <MarketSummaryBanner summary={data.market_summary} />}

      <div className="cycles-grid">
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </div>

      <h2 className="section-title">
        Okazje tradingowe
        <span className="count">{data.opportunities.length}</span>
      </h2>
      {data.opportunities.length === 0 ? (
        <p className="empty-state">Brak aktywnych sygnałów.</p>
      ) : (
        <div className="opportunities-grid">
          {data.opportunities.slice(0, 6).map((opp) => (
            <OpportunityCard key={`${opp.symbol}-${opp.created_at}`} opp={opp} />
          ))}
        </div>
      )}

      <h2 className="section-title">
        Top rynki wg oceny
        <span className="count">{Math.min(5, data.market_assessments?.length ?? 0)}</span>
      </h2>
      <div className="markets-list">
        {(data.market_assessments ?? []).slice(0, 5).map((item) => (
          <div key={item.symbol} className="market-card">
            <div className="market-card-top">
              <div>
                <div className="market-name">{item.name}</div>
                <div className="market-symbol">{item.symbol}</div>
              </div>
              <span className={`signal-tag signal-${item.signal}`}>{SIGNAL_LABELS[item.signal]}</span>
            </div>
            <p className="market-rationale">{item.rationale}</p>
          </div>
        ))}
      </div>
    </>
  )
}
