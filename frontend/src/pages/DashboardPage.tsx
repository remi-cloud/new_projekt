import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { AssetsTable } from '../components/AssetsTable'
import { OpportunityCard } from '../components/OpportunityCard'
import { ErrorState } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'

export function DashboardPage() {
  const { data, error, reload } = useDashboardContext()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  return (
    <>
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
        Notowania
        <span className="count">{data.monitored_assets.length}</span>
      </h2>
      <AssetsTable assets={data.monitored_assets.slice(0, 10)} />
    </>
  )
}
