import { useNavigate } from 'react-router-dom'
import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { ErrorState } from '../components/Loading'
import { OpportunityCard } from '../components/OpportunityCard'
import { TradingPlatformBanner } from '../components/TradingPlatformBanner'
import { useDashboardContext } from '../context/DashboardContext'

export function HomePage() {
  const { data, error, reload, liveConnected, scan, scanning } = useDashboardContext()
  const navigate = useNavigate()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  const topOpps = data.opportunities.slice(0, 3)
  const totalAssets = data.market_summary?.total_assets ?? 0

  const statusLabel = data.scan_in_progress
    ? 'SCAN · IN PROGRESS'
    : data.live_mode && liveConnected
      ? 'TELEMETRIA · LIVE'
      : data.scanner_running
        ? 'SYSTEM · ONLINE'
        : 'SYSTEM · OFFLINE'

  return (
    <div className="home-page">
      <TradingPlatformBanner
        totalAssets={totalAssets}
        signalCount={data.opportunities.length}
        btcSignal={data.bitcoin_cycle.signal}
        marketSummary={data.market_summary}
        statusLabel={statusLabel}
        liveConnected={liveConnected}
        scanning={scanning}
        onScan={scan}
      />

      <div className="home-page-body">
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
    </div>
  )
}
