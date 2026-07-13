import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Loading } from './components/Loading'
import { DashboardProvider, useDashboardContext } from './context/DashboardContext'
import { AboutPage } from './pages/AboutPage'
import { CyclesPage } from './pages/CyclesPage'
import { DashboardPage } from './pages/DashboardPage'
import { HomePage } from './pages/HomePage'
import { MarketsPage } from './pages/MarketsPage'
import { OpportunitiesPage } from './pages/OpportunitiesPage'

function AppShell() {
  const { data, loading, scanning, scan } = useDashboardContext()

  if (loading && !data) {
    return <Loading message="Ładowanie..." />
  }

  return (
    <Layout
      scannerRunning={data?.scanner_running}
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
            <Route path="o-aplikacji" element={<AboutPage />} />
          </Route>
        </Routes>
      </DashboardProvider>
    </BrowserRouter>
  )
}
