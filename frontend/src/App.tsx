import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Loading } from './components/Loading'
import { DashboardProvider, useDashboardContext } from './context/DashboardContext'
import { LocaleProvider, useLocale } from './context/LocaleContext'
import { HomePage } from './pages/HomePage'
import { ALIAS_REDIRECTS } from './routes'

const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const CyclesPage = lazy(() => import('./pages/CyclesPage').then((m) => ({ default: m.CyclesPage })))
const MarketsPage = lazy(() => import('./pages/MarketsPage').then((m) => ({ default: m.MarketsPage })))
const OpportunitiesPage = lazy(() =>
  import('./pages/OpportunitiesPage').then((m) => ({ default: m.OpportunitiesPage })),
)
const PortfolioPage = lazy(() => import('./pages/PortfolioPage').then((m) => ({ default: m.PortfolioPage })))
const InstrumentDetailPage = lazy(() =>
  import('./pages/InstrumentDetailPage').then((m) => ({ default: m.InstrumentDetailPage })),
)
const MacroNewsPage = lazy(() => import('./pages/MacroNewsPage').then((m) => ({ default: m.MacroNewsPage })))
const FinanceAgentPage = lazy(() => import('./pages/FinanceAgentPage').then((m) => ({ default: m.FinanceAgentPage })))
const RoiCalculatorPage = lazy(() =>
  import('./pages/RoiCalculatorPage').then((m) => ({ default: m.RoiCalculatorPage })),
)
const LivePage = lazy(() => import('./pages/LivePage').then((m) => ({ default: m.LivePage })))
const BusinessPage = lazy(() => import('./pages/BusinessPage').then((m) => ({ default: m.BusinessPage })))
const PartnersPage = lazy(() => import('./pages/PartnersPage').then((m) => ({ default: m.PartnersPage })))
const EmbedPage = lazy(() => import('./pages/EmbedPage').then((m) => ({ default: m.EmbedPage })))
const AboutPage = lazy(() => import('./pages/AboutPage').then((m) => ({ default: m.AboutPage })))
const AboutDetailPage = lazy(() => import('./pages/AboutDetailPage').then((m) => ({ default: m.AboutDetailPage })))
const AlertsPage = lazy(() => import('./pages/AlertsPage').then((m) => ({ default: m.AlertsPage })))
const EmbedWidgetPage = lazy(() => import('./pages/EmbedWidgetPage').then((m) => ({ default: m.EmbedWidgetPage })))
const PearlHunterPage = lazy(() =>
  import('./pages/PearlHunterPage').then((m) => ({ default: m.PearlHunterPage })),
)
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })))

function PageSuspense() {
  const { t } = useLocale()
  return (
    <Suspense fallback={<Loading message={t('layout.loading')} />}>
      <Outlet />
    </Suspense>
  )
}

function AppShell() {
  const { data, scanning, scan, liveConnected } = useDashboardContext()

  return (
    <Layout
      scannerRunning={data?.scanner_running}
      scanInProgress={data?.scan_in_progress}
      liveMode={data?.live_mode}
      liveConnected={liveConnected}
      onScan={scan}
      scanning={scanning}
    />
  )
}

export default function App() {
  return (
    <LocaleProvider>
      <BrowserRouter>
        <DashboardProvider>
          <Routes>
            <Route
              path="embed/widget"
              element={
                <Suspense fallback={<Loading message="…" />}>
                  <EmbedWidgetPage />
                </Suspense>
              }
            />
            <Route element={<AppShell />}>
              <Route element={<PageSuspense />}>
                <Route index element={<HomePage />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="cykle" element={<CyclesPage />} />
                <Route path="kalkulator" element={<RoiCalculatorPage />} />
                <Route path="live" element={<LivePage />} />
                <Route path="biznes" element={<BusinessPage />} />
                <Route path="partnerzy" element={<PartnersPage />} />
                <Route path="embed" element={<EmbedPage />} />
                <Route path="news" element={<MacroNewsPage />} />
                <Route path="agent" element={<FinanceAgentPage />} />
                <Route path="okazje" element={<OpportunitiesPage />} />
                <Route path="perly" element={<PearlHunterPage />} />
                <Route path="portfel" element={<PortfolioPage />} />
                <Route path="rynki" element={<MarketsPage />} />
                <Route path="instrument/:symbol" element={<InstrumentDetailPage />} />
                <Route path="o-nas" element={<AboutPage />} />
                <Route path="o-nas/:slug" element={<AboutDetailPage />} />
                <Route path="powiadomienia" element={<AlertsPage />} />
              </Route>
              <Route path="o-aplikacji" element={<Navigate to="/o-nas" replace />} />
              {ALIAS_REDIRECTS.map(({ from, to }) => (
                <Route key={from} path={from} element={<Navigate to={to} replace />} />
              ))}
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </DashboardProvider>
      </BrowserRouter>
    </LocaleProvider>
  )
}
