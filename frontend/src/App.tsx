import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import SingularTracker from './components/SingularTracker'
import AgentsPage from './pages/AgentsPage'
import AlertsPage from './pages/AlertsPage'
import CyclesPage from './pages/CyclesPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import MarketsPage from './pages/MarketsPage'
import OpportunitiesPage from './pages/OpportunitiesPage'
import SuperOpportunitiesPage from './pages/SuperOpportunitiesPage'
import WatchlistPage from './pages/WatchlistPage'

export default function App() {
  return (
    <BrowserRouter>
      <SingularTracker />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="okazje" element={<OpportunitiesPage />} />
          <Route path="superokazje" element={<SuperOpportunitiesPage />} />
          <Route path="superokazje/:symbol" element={<SuperOpportunitiesPage />} />
          <Route path="pozycja/:symbol" element={<SuperOpportunitiesPage />} />
          <Route path="agenci" element={<AgentsPage />} />
          <Route path="modele" element={<CyclesPage />} />
          <Route path="cykle" element={<CyclesPage />} />
          <Route path="historia" element={<HistoryPage />} />
          <Route path="rynki" element={<MarketsPage />} />
          <Route path="watchlista" element={<WatchlistPage />} />
          <Route path="alerty" element={<AlertsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
