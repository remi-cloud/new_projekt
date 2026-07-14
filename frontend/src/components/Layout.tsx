import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { KarDigitalLogo } from './KarDigitalLogo'
import { MOBILE_NAV, NAV_ITEMS } from '../constants'

interface LayoutProps {
  scannerRunning?: boolean
  scanInProgress?: boolean
  liveMode?: boolean
  liveConnected?: boolean
  onScan?: () => Promise<void>
  scanning?: boolean
}

export function Layout({ scannerRunning, scanInProgress, liveMode, liveConnected, onScan, scanning }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [toast, setToast] = useState<string | null>(null)
  const pageTitle = NAV_ITEMS.find((n) => n.path === location.pathname)?.label ?? 'Cyclical Trader'
  const isHome = location.pathname === '/'

  const handleScan = async () => {
    if (!onScan || scanning) return
    try {
      await onScan()
      setToast('Skan w tle — dane odświeżą się za chwilę ✓')
      setTimeout(() => setToast(null), 3500)
    } catch {
      setToast('Błąd skanowania — spróbuj za chwilę')
      setTimeout(() => setToast(null), 3500)
    }
  }

  const statusLabel = scanInProgress
    ? 'SCAN · IN PROGRESS'
    : liveMode && liveConnected
      ? 'TELEMETRY · LIVE'
      : scannerRunning
        ? 'SYSTEM · ONLINE'
        : 'SYSTEM · OFFLINE'

  return (
    <div className="app-shell">
      {toast && <div className="toast">{toast}</div>}

      <aside className="desktop-sidebar">
        <button type="button" className="sidebar-brand tap-target" onClick={() => navigate('/')}>
          <KarDigitalLogo size={48} />
          <span className="sidebar-product">Cyclical Trader</span>
        </button>

        <nav className="sidebar-nav" aria-label="Nawigacja główna">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-nav-item tap-target ${location.pathname === item.path ? 'active' : ''}`}
            >
              {item.label}
            </Link>
          ))}
          <Link
            to="/portfel"
            className={`sidebar-nav-item tap-target ${location.pathname === '/portfel' ? 'active' : ''}`}
          >
            Portfel
          </Link>
        </nav>

        <div className="sidebar-footer">
          <div className={`sidebar-status ${scannerRunning ? 'online' : ''}`}>{statusLabel}</div>
          {onScan && (
            <button
              type="button"
              className="sidebar-scan-btn tap-target"
              onClick={handleScan}
              disabled={scanning}
            >
              {scanning ? 'Skanowanie…' : '↻ Skanuj rynki'}
            </button>
          )}
        </div>
      </aside>

      <div className="app-main">
        <header className={`app-header ${isHome ? 'home-header-hidden' : ''}`}>
          <button type="button" className="mobile-header-left tap-target" onClick={() => navigate('/')}>
            <KarDigitalLogo size={36} compact />
            <div>
              <div className="mobile-title">{pageTitle}</div>
              <div className="mobile-subtitle">{statusLabel}</div>
            </div>
          </button>
          {onScan && (
            <button
              type="button"
              className="mobile-scan-btn tap-target"
              onClick={handleScan}
              disabled={scanning}
              aria-label="Skanuj rynki"
            >
              {scanning ? '…' : '↻'}
            </button>
          )}
        </header>

        <header className={`desktop-header ${isHome ? 'home-header-hidden' : ''}`}>
          <div>
            <h1 className="desktop-page-title">{pageTitle}</h1>
            <p className="desktop-page-subtitle">{statusLabel}</p>
          </div>
          {onScan && (
            <button
              type="button"
              className="btn btn-primary desktop-scan-btn tap-target"
              onClick={handleScan}
              disabled={scanning}
            >
              {scanning ? 'Skanowanie…' : '↻ Skanuj rynki'}
            </button>
          )}
        </header>

        <main className={`app-content ${isHome ? 'app-content-home' : ''}`}>
          <div key={location.pathname} className="page-transition">
            <Outlet />
          </div>
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Nawigacja mobilna">
        {MOBILE_NAV.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`bottom-nav-item tap-target ${location.pathname === item.path ? 'active' : ''}`}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
