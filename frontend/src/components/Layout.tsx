import { Link, Outlet, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { AutoRefreshToggle } from './AutoRefreshToggle'
import { KarDigitalLogo } from './KarDigitalLogo'
import { LanguageSwitcher } from './LanguageSwitcher'
import { SectionTabs } from './SectionTabs'
import { hubForPath, MOBILE_NAV, NAV_ITEMS, navActivePath } from '../constants'
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
  '/agent': 'nav.agent',
  '/narzedzia': 'nav.tools',
  '/narzedzia/singularity': 'nav.singularity',
  '/narzedzia/astra': 'nav.astra',
  '/execution': 'nav.execution',
  '/powiadomienia': 'nav.alerts',
  '/o-nas': 'nav.about',
  '/portfel': 'nav.portfolio',
}

export function Layout({ scannerRunning, scanInProgress, liveMode, liveConnected, onScan, scanning }: LayoutProps) {
  const location = useLocation()
  const { t } = useLocale()
  const [toast, setToast] = useState<string | null>(null)
  const activePath = navActivePath(location.pathname)
  const hub = hubForPath(location.pathname)
  const titleKey: TranslationPath =
    location.pathname.startsWith('/o-nas')
      ? 'nav.about'
      : location.pathname === '/embed'
        ? 'nav.embed'
        : (NAV_KEYS[location.pathname] ?? NAV_KEYS[activePath] ?? 'nav.start')
  const pageTitle = t(titleKey)
  const isHome = location.pathname === '/'

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
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-nav-item tap-target ${activePath === item.path ? 'active' : ''}`}
            >
              {t(item.labelKey)}
            </Link>
          ))}
          <Link
            to="/portfel"
            className={`sidebar-nav-item tap-target ${activePath === '/portfel' ? 'active' : ''}`}
          >
            {t('nav.portfolio')}
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

        <main className={`app-content ${isHome ? 'app-content-home' : ''}`}>
          {hub && <SectionTabs tabs={hub.tabs} />}
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
            className={`bottom-nav-item tap-target ${activePath === item.path || location.pathname === item.path ? 'active' : ''}`}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{t(NAV_KEYS[item.path] ?? 'nav.start')}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
