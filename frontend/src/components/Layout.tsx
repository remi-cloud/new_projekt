import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { MOBILE_NAV, NAV_ITEMS } from '../constants'

interface LayoutProps {
  scannerRunning?: boolean
  liveMode?: boolean
  liveConnected?: boolean
  onScan?: () => Promise<void>
  scanning?: boolean
}

export function Layout({ scannerRunning, liveMode, liveConnected, onScan, scanning }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [toast, setToast] = useState<string | null>(null)
  const pageTitle = NAV_ITEMS.find((n) => n.path === location.pathname)?.label ?? 'Cyclical Trader'

  const handleScan = async () => {
    if (!onScan || scanning) return
    try {
      await onScan()
      setToast('Skan zakończony ✓')
      setTimeout(() => setToast(null), 2500)
    } catch {
      setToast('Błąd skanowania')
      setTimeout(() => setToast(null), 2500)
    }
  }

  return (
    <div className="app-shell">
      {toast && <div className="toast">{toast}</div>}

      <header className="mobile-header">
        <button type="button" className="mobile-header-left tap-target" onClick={() => navigate('/')}>
          <span className="mobile-logo">↻</span>
          <div>
            <div className="mobile-title">{pageTitle}</div>
            <div className="mobile-subtitle">
              {liveMode && liveConnected
                ? '● Live realtime'
                : scannerRunning
                  ? '● Live 24/7'
                  : '○ Offline'}
            </div>
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

      <main className="mobile-content">
        <Outlet />
      </main>

      <nav className="bottom-nav" aria-label="Nawigacja">
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
