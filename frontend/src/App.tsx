import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import CyclesPage from './pages/CyclesPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import MarketsPage from './pages/MarketsPage'
import OpportunitiesPage from './pages/OpportunitiesPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="okazje" element={<OpportunitiesPage />} />
          <Route path="cykle" element={<CyclesPage />} />
          <Route path="historia" element={<HistoryPage />} />
          <Route path="rynki" element={<MarketsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
