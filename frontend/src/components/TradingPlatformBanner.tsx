import { useNavigate } from 'react-router-dom'
import { KarDigitalLogo } from './KarDigitalLogo'
import { SIGNAL_LABELS } from '../constants'
import { MarketSummary } from '../types'

interface TradingPlatformBannerProps {
  totalAssets: number
  signalCount: number
  btcSignal: keyof typeof SIGNAL_LABELS
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
  const navigate = useNavigate()
  const outlookClass =
    marketSummary?.outlook === 'bullish'
      ? 'bullish'
      : marketSummary?.outlook === 'bearish'
        ? 'bearish'
        : 'mixed'

  return (
    <section className="trading-platform-banner" aria-label="KAR digital — platforma tradingowa">
      <div className="trading-banner-orbit trading-banner-orbit-1" aria-hidden />
      <div className="trading-banner-orbit trading-banner-orbit-2" aria-hidden />
      <div className="trading-banner-grid" aria-hidden />
      <div className="trading-banner-scan" aria-hidden />

      <div className="trading-banner-shell">
        <div className="trading-banner-topbar">
          <div className="trading-banner-topbar-left">
            <h1 className="trading-banner-page-title">Start</h1>
            <p className="trading-banner-page-subtitle">{statusLabel}</p>
          </div>
          {onScan && (
            <button
              type="button"
              className="btn btn-primary trading-banner-scan-btn tap-target"
              onClick={onScan}
              disabled={scanning}
            >
              {scanning ? 'Skanowanie…' : '↻ Skanuj rynki'}
            </button>
          )}
        </div>

        {marketSummary && (
          <div className={`trading-banner-market ${outlookClass}`}>
            <div className="trading-banner-market-title">
              Ocena globalna · {marketSummary.total_assets} instrumentów
            </div>
            <div className="trading-banner-market-text">{marketSummary.outlook_label}</div>
            <div className="trading-banner-market-stats">
              <span className="stat-buy">Kupuj: {marketSummary.by_signal.buy ?? 0}</span>
              <span>Obserwuj: {marketSummary.by_signal.watch ?? 0}</span>
              <span>Trzymaj: {marketSummary.by_signal.hold ?? 0}</span>
              <span className="stat-sell">Sprzedaj: {marketSummary.by_signal.sell ?? 0}</span>
            </div>
          </div>
        )}

        <div className="trading-banner-inner">
          <div className="trading-banner-logo-wrap">
            <KarDigitalLogo size={132} variant="hero" />
            <div className="trading-banner-status">
              <span className={`trading-banner-live-dot ${liveConnected ? 'on' : ''}`} />
              {liveConnected ? 'TELEMETRIA · LIVE' : 'SYSTEM · ONLINE'}
            </div>
          </div>

          <div className="trading-banner-body">
            <p className="trading-banner-eyebrow">Institutional Research · Paper Trading · Live Charts</p>
            <h2 className="trading-banner-title">
              Platforma do <span>tradingu cyklicznego</span>
            </h2>
            <p className="trading-banner-desc">
              Analiza faz rynku, sygnały WEJ/WYJ, portfel papierowy i wykresy TradingView — jeden terminal
              dla {totalAssets} instrumentów na świecie.
            </p>

            <div className="trading-banner-chips">
              <span className="trading-banner-chip">Cykle · RSI</span>
              <span className="trading-banner-chip">Paper portfel</span>
              <span className="trading-banner-chip">TradingView Live</span>
              <span className="trading-banner-chip">Sygnały AI</span>
            </div>

            <div className="trading-banner-actions">
              <button
                type="button"
                className="btn btn-primary btn-lg tap-target"
                onClick={() => navigate('/dashboard')}
              >
                Otwórz panel
              </button>
              <button type="button" className="btn btn-ghost tap-target" onClick={() => navigate('/rynki')}>
                Rynki globalne ({totalAssets})
              </button>
              <button type="button" className="btn btn-ghost tap-target" onClick={() => navigate('/portfel')}>
                Portfel papierowy
              </button>
              <button type="button" className="btn btn-ghost tap-target" onClick={() => navigate('/o-nas')}>
                O nas
              </button>
            </div>

            <div className="trading-banner-stats">
              <div className="trading-banner-stat">
                <div className="trading-banner-stat-value">{totalAssets}</div>
                <div className="trading-banner-stat-label">Instrumentów</div>
              </div>
              <div className="trading-banner-stat">
                <div className="trading-banner-stat-value">{signalCount}</div>
                <div className="trading-banner-stat-label">Sygnałów</div>
              </div>
              <div className="trading-banner-stat">
                <div className="trading-banner-stat-value">{SIGNAL_LABELS[btcSignal]}</div>
                <div className="trading-banner-stat-label">BTC cykl</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
