import { Link, Outlet, useLocation } from 'react-router-dom'
import { NAV_ITEMS } from '../constants'

interface LayoutProps {
  scannerRunning?: boolean
  lastScanAt?: string | null
  onScan?: () => void
  scanning?: boolean
}

export function Layout({ scannerRunning, lastScanAt, onScan, scanning }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="www-shell">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-icon">↻</span>
          <div>
            <div className="brand-name">Cyclical</div>
            <div className="brand-sub">Trader</div>
          </div>
        </Link>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          {scannerRunning !== undefined && (
            <div className="status-badge compact">
              <span className={`status-dot ${scannerRunning ? '' : 'offline'}`} />
              Skaner {scannerRunning ? '24/7' : 'offline'}
            </div>
          )}
          {lastScanAt && (
            <div className="last-scan">
              Ostatni skan:<br />
              {new Date(lastScanAt).toLocaleString('pl-PL')}
            </div>
          )}
          {onScan && (
            <button className="btn btn-primary btn-block" onClick={onScan} disabled={scanning}>
              {scanning ? 'Skanowanie...' : 'Skanuj teraz'}
            </button>
          )}
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title">
            {NAV_ITEMS.find((n) => n.path === location.pathname)?.label ?? 'Cyclical Trader'}
          </div>
          <div className="topbar-meta">
            <span className="live-badge">LIVE</span>
            <span className="topbar-note">Monitorowanie cykli rynkowych</span>
          </div>
        </header>
        <main className="page-content">
          <Outlet />
        </main>
        <footer className="site-footer">
          Cyclical Trader · Cykl BTC 364/1064 dni · Cykl prezydencki USA · Nie jest to porada inwestycyjna
        </footer>
      </div>
    </div>
  )
}
