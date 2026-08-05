import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api'
import { LocaleProvider } from '../context/LocaleContext'
import type { PaperPortfolio } from '../types'
import { PortfolioPage } from './PortfolioPage'

const reload = vi.fn(async () => undefined)

const emptyPortfolio: PaperPortfolio = {
  cash_pln: 1_000_000,
  initial_cash_pln: 1_000_000,
  positions_value_pln: 0,
  total_equity_pln: 1_000_000,
  unrealized_pnl_pln: 0,
  realized_pnl_pln: 0,
  total_pnl_pln: 0,
  total_pnl_pct: 0,
  usd_pln_rate: 4.0,
  positions_count: 0,
  positions: [],
  closed_positions_count: 0,
  closed_positions: [],
  limit_orders: [],
  recent_trades: [],
  quotes_available: 0,
}

vi.mock('../components/PaperTrading', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../components/PaperTrading')>()
  return {
    ...actual,
    usePaperPortfolio: () => ({
      portfolio: emptyPortfolio,
      loading: false,
      error: null,
      reload,
    }),
  }
})

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    resetPaperPortfolio: vi.fn(),
    purgeAgentPaperPositions: vi.fn(),
    cancelPaperOrder: vi.fn(),
    cancelAllPaperOrders: vi.fn(),
  }
})

function renderPage() {
  return render(
    <LocaleProvider>
      <MemoryRouter initialEntries={['/portfel']}>
        <Routes>
          <Route path="/portfel" element={<PortfolioPage />} />
        </Routes>
      </MemoryRouter>
    </LocaleProvider>,
  )
}

describe('PortfolioPage', () => {
  beforeEach(() => {
    reload.mockClear()
    vi.mocked(api.resetPaperPortfolio).mockReset()
    vi.mocked(api.resetPaperPortfolio).mockResolvedValue(emptyPortfolio)
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true),
    )
  })

  it('shows paper banner cash and quick trade links', () => {
    renderPage()
    expect(screen.getByText(/Paper · 1[,.\s]?000[,.\s]?000 PLN/i)).toBeTruthy()
    expect(screen.getByRole('link', { name: /Bitcoin/i }).getAttribute('href')).toBe(
      '/instrument/BTC-USD',
    )
    expect(document.querySelector('a[href="/instrument/AAPL"]')).toBeTruthy()
    expect(document.querySelector('a[href="/instrument/AAPLX-USD"]')).toBeTruthy()
    expect(document.querySelector('a[href="/instrument/NVDA"]')).toBeTruthy()
    expect(document.querySelector('.portfolio-empty-cta')?.textContent).toMatch(
      /Pick BTC|Wybierz BTC/i,
    )
  })

  it('calls reset API after confirm', async () => {
    renderPage()
    fireEvent.click(
      screen.getByRole('button', { name: /Reset to 1,000,000 PLN|Reset do 1 000 000 PLN/i }),
    )
    await waitFor(() => {
      expect(api.resetPaperPortfolio).toHaveBeenCalledTimes(1)
    })
    expect(reload).toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.getByText(/Portfolio reset|Portfel zresetowany/i)).toBeTruthy()
    })
  })
})
