import { Link, Outlet, useLocation } from 'react-router-dom'
import { NAV_ITEMS } from '../constants'

interface LayoutProps {
  scannerRunning?: boolean
  onScan?: () => void
  scanning?: boolean
}

const MOBILE_NAV = [
  { path: '/', label: 'Start', icon: '⌂' },
  { path: '/dashboard', label: 'Panel', icon: '◫' },
  { path: '/okazje', label: 'Okazje', icon: '◎' },
  { path: '/rynki', label: 'Rynki', icon: '▤' },
  { path: '/cykle', label: 'Cykle', icon: '↻' },
]

export function Layout({ scannerRunning, onScan, scanning }: LayoutProps) {
  const location = useLocation()
  const pageTitle = NAV_ITEMS.find((n) => n.path === location.pathname)?.label ?? 'Cyclical Trader'

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <div className="mobile-header-left">
          <span className="mobile-logo">↻</span>
          <div>
            <div className="mobile-title">{pageTitle}</div>
            <div className="mobile-subtitle">
              {scannerRunning ? '● Live 24/7' : '○ Offline'}
            </div>
          </div>
        </div>
        {onScan && (
          <button className="mobile-scan-btn" onClick={onScan} disabled={scanning}>
            {scanning ? '…' : '↻'}
          </button>
        )}
      </header>

      <main className="mobile-content">
        <Outlet />
      </main>

      <nav className="bottom-nav">
        {MOBILE_NAV.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`bottom-nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
