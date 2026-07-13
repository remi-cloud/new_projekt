import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Loading } from './components/Loading'
import { DashboardProvider, useDashboardContext } from './context/DashboardContext'
import { AboutPage } from './pages/AboutPage'
import { AlertsPage } from './pages/AlertsPage'
import { CyclesPage } from './pages/CyclesPage'
import { DashboardPage } from './pages/DashboardPage'
import { HomePage } from './pages/HomePage'
import { MarketsPage } from './pages/MarketsPage'
import { OpportunitiesPage } from './pages/OpportunitiesPage'
import { InstrumentDetailPage } from './pages/InstrumentDetailPage'

function AppShell() {
  const { data, loading, scanning, scan, liveConnected } = useDashboardContext()

  if (loading && !data) {
    return <Loading message="Ładowanie..." />
  }

  return (
    <Layout
      scannerRunning={data?.scanner_running}
      liveMode={data?.live_mode}
      liveConnected={liveConnected}
      onScan={scan}
      scanning={scanning}
    />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <DashboardProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="cykle" element={<CyclesPage />} />
            <Route path="okazje" element={<OpportunitiesPage />} />
            <Route path="rynki" element={<MarketsPage />} />
            <Route path="instrument/:symbol" element={<InstrumentDetailPage />} />
            <Route path="o-aplikacji" element={<AboutPage />} />
            <Route path="powiadomienia" element={<AlertsPage />} />
          </Route>
        </Routes>
      </DashboardProvider>
    </BrowserRouter>
  )
}
