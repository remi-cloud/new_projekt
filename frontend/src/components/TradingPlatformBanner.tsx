import { Link } from 'react-router-dom'
import { KarDigitalLogo } from './KarDigitalLogo'
import { MarketSummary } from '../types'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'

interface TradingPlatformBannerProps {
  totalAssets: number
  signalCount: number
  btcSignal: 'buy' | 'sell' | 'hold' | 'watch'
  marketSummary?: MarketSummary | null
  statusLabel: string
  liveConnected?: boolean
  scanning?: boolean
  onScan?: () => Promise<void>
}

export function TradingPlatformBanner({
  totalAssets,
  signalCount,
  btcSignal,
  marketSummary,
  statusLabel,
  liveConnected,
  scanning,
  onScan,
}: TradingPlatformBannerProps) {
  const { t } = useLocale()
  const { signal } = useDomainLabels()
  const outlookClass =
    marketSummary?.outlook === 'bullish'
      ? 'bullish'
      : marketSummary?.outlook === 'bearish'
        ? 'bearish'
        : 'mixed'

  const outlookText =
    marketSummary?.outlook === 'bullish'
      ? t('banner.outlookBullish')
      : marketSummary?.outlook === 'bearish'
        ? t('banner.outlookBearish')
        : t('banner.outlookMixed')

  return (
    <section className="trading-platform-banner academy-office-banner" aria-label={t('banner.ariaLabel')}>
      <div className="trading-banner-visual" aria-hidden>
        <img
          className="trading-banner-photo"
          src="/banner-robot-office.png"
          alt=""
          width={1536}
          height={864}
          decoding="async"
          fetchPriority="high"
        />
        <div className="trading-banner-scrim" />
      </div>

      <div className="trading-banner-shell">
        <div className="trading-banner-topbar">
          <div className="trading-banner-topbar-left">
            <h1 className="trading-banner-page-title">{t('layout.brand')}</h1>
            <p className="trading-banner-page-subtitle">{statusLabel}</p>
          </div>
          {onScan && (
            <button
              type="button"
              className="btn btn-primary trading-banner-scan-btn tap-target"
              onClick={onScan}
              disabled={scanning}
            >
              {scanning ? t('banner.scanning') : t('banner.scan')}
            </button>
          )}
        </div>

        {marketSummary && (
          <div className={`trading-banner-market ${outlookClass}`}>
            <div className="trading-banner-market-title">
              {t('banner.globalAssessment', { n: marketSummary.total_assets })}
            </div>
            <div className="trading-banner-market-text">{outlookText}</div>
            <div className="trading-banner-market-stats">
              <span className="stat-buy">
                {t('banner.buyCount', { n: marketSummary.by_signal.buy ?? 0 })}
              </span>
              <span>{t('banner.watchCount', { n: marketSummary.by_signal.watch ?? 0 })}</span>
              <span>{t('banner.holdCount', { n: marketSummary.by_signal.hold ?? 0 })}</span>
              <span className="stat-sell">
                {t('banner.sellCount', { n: marketSummary.by_signal.sell ?? 0 })}
              </span>
            </div>
          </div>
        )}

        <div className="trading-banner-inner">
          <div className="trading-banner-logo-wrap">
            <KarDigitalLogo size={132} variant="hero" />
            <div className="trading-banner-status">
              <span className={`trading-banner-live-dot ${liveConnected ? 'on' : ''}`} />
              {liveConnected ? t('layout.statusLive') : t('layout.statusOnline')}
            </div>
          </div>

          <div className="trading-banner-body">
            <p className="trading-banner-eyebrow">{t('banner.eyebrow')}</p>
            <h2 className="trading-banner-title">
              {(() => {
                const full = t('banner.headline')
                const span = t('banner.headlineSpan')
                const i = full.indexOf(span)
                if (i < 0) return full
                return (
                  <>
                    {full.slice(0, i)}
                    <span>{span}</span>
                    {full.slice(i + span.length)}
                  </>
                )
              })()}
            </h2>
            <p className="trading-banner-desc">{t('banner.desc', { n: totalAssets })}</p>

            <div className="trading-banner-chips">
              <span className="trading-banner-chip">{t('banner.chip1')}</span>
              <span className="trading-banner-chip">{t('banner.chip2')}</span>
              <span className="trading-banner-chip">{t('banner.chip3')}</span>
              <span className="trading-banner-chip">{t('banner.chip4')}</span>
            </div>

            <div className="trading-banner-actions">
              <Link to="/dashboard" className="btn btn-primary btn-lg tap-target card-nav-link">
                {t('banner.openDashboard')}
              </Link>
              <Link to="/rynki" className="btn btn-ghost tap-target card-nav-link">
                {t('banner.globalMarkets', { n: totalAssets })}
              </Link>
              <Link to="/portfel" className="btn btn-ghost tap-target card-nav-link">
                {t('banner.paperPortfolio')}
              </Link>
              <Link to="/o-nas" className="btn btn-ghost tap-target card-nav-link">
                {t('banner.about')}
              </Link>
            </div>

            <div className="trading-banner-stats">
              <div className="trading-banner-stat">
                <div className="trading-banner-stat-value">{totalAssets}</div>
                <div className="trading-banner-stat-label">{t('banner.statInstruments')}</div>
              </div>
              <div className="trading-banner-stat">
                <div className="trading-banner-stat-value">{signalCount}</div>
                <div className="trading-banner-stat-label">{t('banner.statSignals')}</div>
              </div>
              <div className="trading-banner-stat">
                <div className="trading-banner-stat-value">{signal[btcSignal]}</div>
                <div className="trading-banner-stat-label">{t('banner.btcCycle')}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
