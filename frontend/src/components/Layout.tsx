import { Link, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { AutoRefreshToggle } from './AutoRefreshToggle'
import { KarDigitalLogo } from './KarDigitalLogo'
import { LanguageSwitcher } from './LanguageSwitcher'
import { SectionTabs } from './SectionTabs'
import { MOBILE_NAV, NAV_SECTIONS, navActivePath, sectionForPath } from '../constants'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from '../i18n'

interface LayoutProps {
  scannerRunning?: boolean
  scanInProgress?: boolean
  liveMode?: boolean
  liveConnected?: boolean
  onScan?: () => Promise<void>
  scanning?: boolean
}

const NAV_KEYS: Record<string, TranslationPath> = {
  '/': 'nav.start',
  '/dashboard': 'nav.panel',
  '/rynki': 'nav.markets',
  '/okazje': 'nav.opportunities',
  '/superokazje': 'nav.super',
  '/cykle': 'nav.cycles',
  '/kalkulator': 'nav.calculator',
  '/live': 'nav.live',
  '/biznes': 'nav.business',
  '/partnerzy': 'nav.partners',
  '/embed': 'nav.embed',
  '/news': 'nav.news',
  '/ai-hacking': 'nav.aiHacking',
  '/radar': 'nav.radar',
  '/agent': 'nav.agent',
  '/narzedzia': 'nav.tools',
  '/narzedzia/singularity': 'nav.singularity',
  '/narzedzia/astra': 'nav.astra',
  '/execution': 'nav.execution',
  '/powiadomienia': 'nav.alerts',
  '/o-nas': 'nav.about',
  '/portfel': 'nav.portfolio',
  '/perly': 'nav.pearls',
  '/fomo': 'nav.fomo',
  '/axiom': 'nav.axiom',
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
  const titleKey: TranslationPath = activeLink?.labelKey
    ?? (location.pathname.startsWith('/o-nas') ? 'nav.about' : NAV_KEYS[location.pathname] ?? 'nav.start')
  const pageTitle = t(titleKey)
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
          <KarDigitalLogo size={64} />
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
          {onScan && (
            <button
              type="button"
              className="sidebar-scan-btn tap-target"
              onClick={handleScan}
              disabled={scanning}
            >
              {scanning ? t('layout.scanning') : t('layout.scan')}
            </button>
          )}
        </div>
      </aside>

      <div className="app-main">
        <header className={`app-header ${isHome ? 'home-header-hidden' : ''}`}>
          <Link to="/" className="mobile-header-left tap-target card-nav-link">
            <KarDigitalLogo size={36} compact />
            <div>
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
            <LanguageSwitcher compact />
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
            <p className="desktop-page-subtitle">{statusLabel}</p>
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
          <span className="bottom-nav-label">{menuOpen ? t('layout.menuClose') : t('layout.menu')}</span>
        </button>
      </nav>
    </div>
  )
}
