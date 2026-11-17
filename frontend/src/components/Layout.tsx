import { Link, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { AutoRefreshToggle } from './AutoRefreshToggle'
import { KarDigitalLogo } from './KarDigitalLogo'
import { LanguageSwitcher } from './LanguageSwitcher'
import { SectionTabs } from './SectionTabs'
import { MOBILE_NAV, NAV_SECTIONS, navActivePath, sectionForPath } from '../constants'
import { shellTitle } from '../lib/pageTitle'
import { useLocale } from '../context/LocaleContext'

interface LayoutProps {
  scannerRunning?: boolean
  scanInProgress?: boolean
  liveMode?: boolean
  liveConnected?: boolean
  onScan?: () => Promise<void>
  scanning?: boolean
}

function NavSections({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useLocale()
  const { pathname } = useLocation()
  const active = navActivePath(pathname)

  return (
    <div className="nav-sections">
      {NAV_SECTIONS.map((section) => (
        <div key={section.id} className="nav-section">
          <p className="nav-section-label">{t(section.labelKey)}</p>
          {section.items.map((item) => {
            const isActive = active === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-nav-item tap-target ${isActive ? 'active' : ''}`}
                aria-current={isActive ? 'page' : undefined}
                onClick={onNavigate}
              >
                {t(item.labelKey)}
              </Link>
            )
          })}
        </div>
      ))}
    </div>
  )
}

export function Layout({ scannerRunning, scanInProgress, liveMode, liveConnected, onScan, scanning }: LayoutProps) {
  const location = useLocation()
  const { t } = useLocale()
  const [toast, setToast] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const activePath = navActivePath(location.pathname)
  const section = sectionForPath(location.pathname)
  const activeLink = section?.items.find((item) => item.path === activePath)
  const pageTitle = shellTitle(location.pathname, t)
  const isHome = location.pathname === '/'

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  const handleScan = async () => {
    if (!onScan || scanning) return
    try {
      await onScan()
      setToast(t('layout.scanDone'))
      setTimeout(() => setToast(null), 3500)
    } catch {
      setToast(t('layout.scanError'))
      setTimeout(() => setToast(null), 3500)
    }
  }

  const statusLabel = scanInProgress
    ? t('layout.statusScan')
    : liveMode && liveConnected
      ? t('layout.statusLive')
      : scannerRunning
        ? t('layout.statusOnline')
        : t('layout.statusOffline')

  return (
    <div className="app-shell">
      {toast && <div className="toast">{toast}</div>}

      <aside className="desktop-sidebar">
        <Link to="/" className="sidebar-brand tap-target card-nav-link">
          <KarDigitalLogo size={40} showText={false} />
          <span className="sidebar-product">{t('layout.brand')}</span>
        </Link>

        <div className="sidebar-lang">
          <LanguageSwitcher />
          <AutoRefreshToggle />
        </div>

        <nav className="sidebar-nav" aria-label={t('layout.navMain')}>
          <NavSections />
        </nav>

        <div className="sidebar-footer">
          <div className={`sidebar-status ${scannerRunning ? 'online' : ''}`}>{statusLabel}</div>
        </div>
      </aside>

      <div className="app-main">
        <header className={`app-header ${isHome ? 'home-header-hidden' : ''}`}>
          <Link to="/" className="mobile-header-left tap-target card-nav-link">
            <KarDigitalLogo size={28} showText={false} compact />
            <div className="mobile-header-titles">
              <div className="mobile-title">{pageTitle}</div>
              <div className="mobile-subtitle">{statusLabel}</div>
            </div>
          </Link>
          <div className="mobile-header-actions">
            <button
              type="button"
              className="mobile-menu-btn tap-target"
              aria-expanded={menuOpen}
              aria-controls="mobile-drawer"
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? t('layout.menuClose') : t('layout.menu')}
            </button>
            {onScan && (
              <button
                type="button"
                className="mobile-scan-btn tap-target"
                onClick={handleScan}
                disabled={scanning}
                aria-label={t('layout.scan')}
              >
                {scanning ? '…' : '↻'}
              </button>
            )}
          </div>
        </header>

        <header className={`desktop-header ${isHome ? 'home-header-hidden' : ''}`}>
          <div>
            <h1 className="desktop-page-title">{pageTitle}</h1>
          </div>
          <div className="desktop-header-actions">
            {onScan && (
              <button
                type="button"
                className="btn btn-primary desktop-scan-btn tap-target"
                onClick={handleScan}
                disabled={scanning}
              >
                {scanning ? t('layout.scanning') : t('layout.scan')}
              </button>
            )}
          </div>
        </header>

        <nav
          id="mobile-drawer"
          className={`mobile-drawer ${menuOpen ? 'is-open' : ''}`}
          aria-label={t('layout.menu')}
          hidden={!menuOpen}
        >
          <div className="mobile-drawer-lang">
            <LanguageSwitcher />
          </div>
          <NavSections onNavigate={() => setMenuOpen(false)} />
        </nav>

        <main className={`app-content ${isHome ? 'app-content-home' : ''}`}>
          {!isHome && section && activeLink && section.labelKey !== activeLink.labelKey && (
            <p className="page-crumbs">
              <span>{t(section.labelKey)}</span>
              <span className="page-crumbs-sep" aria-hidden="true">/</span>
              <span>{pageTitle}</span>
            </p>
          )}
          {section && <SectionTabs tabs={section.items} />}
          <div key={location.pathname} className="page-transition">
            <Outlet />
          </div>
        </main>
      </div>

      <nav className="bottom-nav" aria-label={t('layout.navMobile')}>
        {MOBILE_NAV.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`bottom-nav-item tap-target ${activePath === item.path ? 'active' : ''}`}
            aria-current={activePath === item.path ? 'page' : undefined}
          >
            <span className="bottom-nav-label">{t(item.labelKey)}</span>
          </Link>
        ))}
        <button
          type="button"
          className={`bottom-nav-item tap-target ${menuOpen ? 'active' : ''}`}
          aria-expanded={menuOpen}
          aria-controls="mobile-drawer"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="bottom-nav-label">{t('layout.menu')}</span>
        </button>
      </nav>
    </div>
  )
}
