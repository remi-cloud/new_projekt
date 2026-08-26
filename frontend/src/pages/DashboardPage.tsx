import { Link } from 'react-router-dom'
import { AskAgentButton } from '../components/AskAgentButton'
import { CommunityActions } from '../components/CommunityActions'
import { InstrumentShareMenu } from '../components/InstrumentShareMenu'
import { AgentTelemetryStrip } from '../components/AgentTelemetryStrip'
import { CoordinatorHealthStrip } from '../components/CoordinatorHealthStrip'
import { FomoGhostStrip } from '../components/FomoGhostStrip'
import { LaunchScoutStrip } from '../components/LaunchScoutStrip'
import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { MarketSummaryBanner } from '../components/MarketAssessmentCard'
import { ProgramUsBacktestPanel } from '../components/ProgramUsBacktestPanel'
import { OpportunityCard } from '../components/OpportunityCard'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'

export function DashboardPage() {
  const { data, error, reload, loading } = useDashboardContext()
  const { t } = useLocale()
  const { signal } = useDomainLabels()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (loading && !data) return <Loading message={t('layout.loading')} />
  if (!data) return null

  const momentumPicks = data.opportunities.filter((o) => o.is_momentum_pick)

  return (
    <div className="dashboard-page">
      {data.market_summary && (
        <section className="dashboard-section dashboard-summary">
          <MarketSummaryBanner summary={data.market_summary} />
        </section>
      )}

      <AgentTelemetryStrip />
      <CoordinatorHealthStrip />
      <FomoGhostStrip />
      <LaunchScoutStrip />
      <ProgramUsBacktestPanel />

      <section className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">{t('dashboard.marketCycles')}</h2>
        </div>
        <div className="cycles-grid">
          <CycleCardBitcoin cycle={data.bitcoin_cycle} />
          <CycleCardPresidential cycle={data.presidential_cycle} />
        </div>
      </section>

      <section className="dashboard-section desk-teaser">
        <div className="section-header">
          <h2 className="section-title">{t('launch.homeTitle')}</h2>
          <Link to="/launch" className="link-btn tap-target card-nav-link">
            {t('launch.openDesk')}
          </Link>
        </div>
        <p className="pearl-lead launch-quote">{t('launch.quote')}</p>
        <p className="page-lead">{t('launch.homeLead')}</p>
        <div className="desk-teaser-actions">
          <Link to="/launch" className="btn btn-primary tap-target card-nav-link">
            {t('launch.homeCta')}
          </Link>
          <Link to="/superokazje" className="btn tap-target card-nav-link">
            {t('nav.super')}
          </Link>
          <Link to="/narzedzia/singularity" className="btn tap-target card-nav-link">
            Singularity
          </Link>
        </div>
      </section>

      <div className="dashboard-columns">
        <section className="dashboard-section dashboard-section-main">
          <div className="section-header">
            <h2 className="section-title">
              {t('dashboard.tradingOpportunities')}
              <span className="count">{data.opportunities.length}</span>
            </h2>
            <Link to="/okazje" className="link-btn tap-target card-nav-link">
              {t('dashboard.seeAll')}
            </Link>
          </div>
          {data.opportunities.length === 0 ? (
            <p className="empty-state">{t('dashboard.emptySignals')}</p>
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
              <h3 className="side-panel-title">{t('dashboard.momentumTitle')}</h3>
              <p className="side-panel-desc">{t('dashboard.momentumDesc')}</p>
              <div className="momentum-list">
                {momentumPicks.slice(0, 5).map((opp) => (
                  <div key={`mom-${opp.symbol}`} className="momentum-item-wrap">
                    <Link
                      to={`/instrument/${encodeURIComponent(opp.symbol)}`}
                      className="momentum-item tap-target card-nav-link"
                    >
                      <div className="momentum-item-top">
                        <span className="momentum-item-name">{opp.name}</span>
                        <span className={`signal-tag signal-${opp.action}`}>{signal[opp.action]}</span>
                      </div>
                      <div className="momentum-item-meta">
                        {opp.momentum_score != null && (
                          <span>
                            {t('dashboard.momentumShort')} {opp.momentum_score.toFixed(0)}
                          </span>
                        )}
                        <span>{t('dashboard.confidencePct', { n: opp.confidence })}</span>
                      </div>
                    </Link>
                    <div className="momentum-item-share dash-agent-actions">
                      <AskAgentButton mode="instrument" symbol={opp.symbol} name={opp.name} compact />
                      <CommunityActions
                        symbol={opp.symbol}
                        name={opp.name}
                        community={opp.community}
                        compact
                      />
                      <InstrumentShareMenu
                        symbol={opp.symbol}
                        name={opp.name}
                        kind="instrument"
                        signal={signal[opp.action]}
                        compact
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="side-panel">
            <h3 className="side-panel-title">{t('dashboard.topMarkets')}</h3>
            <div className="markets-list markets-list-compact">
              {(data.market_assessments ?? []).slice(0, 5).map((item) => (
                <div key={item.symbol} className="market-card-wrap">
                  <Link
                    to={`/instrument/${encodeURIComponent(item.symbol)}`}
                    className="market-card market-card-clickable tap-target card-nav-link"
                  >
                    <div className="market-card-top">
                      <div>
                        <div className="market-name">{item.name}</div>
                        <div className="market-symbol">{item.symbol}</div>
                      </div>
                      <span className={`signal-tag signal-${item.signal}`}>{signal[item.signal]}</span>
                    </div>
                    {item.momentum_score != null && (
                      <div className="market-momentum">
                        {t('dashboard.momentum', { n: item.momentum_score.toFixed(0) })}
                      </div>
                    )}
                  </Link>
                  <div className="market-card-share dash-agent-actions">
                    <AskAgentButton mode="instrument" symbol={item.symbol} name={item.name} compact />
                    <CommunityActions
                      symbol={item.symbol}
                      name={item.name}
                      community={item.community}
                      compact
                    />
                    <InstrumentShareMenu
                      symbol={item.symbol}
                      name={item.name}
                      kind="instrument"
                      signal={signal[item.signal]}
                      compact
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
