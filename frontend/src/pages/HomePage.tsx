import { useNavigate } from 'react-router-dom'
import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { ErrorState, Loading } from '../components/Loading'
import { OpportunityCard } from '../components/OpportunityCard'
import { InvestmentShowcase } from '../components/InvestmentShowcase'
import { TradingPlatformBanner } from '../components/TradingPlatformBanner'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'

export function HomePage() {
  const { data, error, reload, liveConnected, scan, scanning, loading } = useDashboardContext()
  const navigate = useNavigate()
  const { t } = useLocale()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (loading && !data) return <Loading message={t('layout.loading')} />
  if (!data) {
    return (
      <ErrorState message={t('layout.loading')} onRetry={reload} />
    )
  }

  const topOpps = data.opportunities.slice(0, 3)
  const totalAssets = data.market_summary?.total_assets ?? 0

  const statusLabel = data.scan_in_progress
    ? t('layout.statusScan')
    : data.live_mode && liveConnected
      ? t('layout.statusLive')
      : data.scanner_running
        ? t('layout.statusOnline')
        : t('layout.statusOffline')

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
        <InvestmentShowcase />

        <section className="home-cycles">
          <CycleCardBitcoin cycle={data.bitcoin_cycle} />
          <CycleCardPresidential cycle={data.presidential_cycle} />
        </section>

        {topOpps.length > 0 && (
          <section>
            <div className="section-header">
              <h2 className="section-title">{t('home.topOpportunities')}</h2>
              <button type="button" className="link-btn tap-target" onClick={() => navigate('/okazje')}>
                {t('home.seeAll')}
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
