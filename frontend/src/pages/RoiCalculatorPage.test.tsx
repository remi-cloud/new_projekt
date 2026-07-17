import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api'
import { LocaleProvider } from '../context/LocaleContext'
import type { RoiAssetInfo, RoiCalculateResult } from '../types'
import { RoiCalculatorPage } from './RoiCalculatorPage'

vi.mock('../components/RoiEquityChart', () => ({
  RoiEquityChart: () => null,
}))
vi.mock('../components/GrowthFunnelStrip', () => ({
  GrowthFunnelStrip: () => null,
}))
vi.mock('../components/RoiShareCard', () => ({
  RoiShareCard: () => null,
}))

vi.mock('../api', () => ({
  fetchRoiAssets: vi.fn(),
  calculateRoi: vi.fn(),
}))

const mockAssets: RoiAssetInfo[] = [
  {
    symbol: 'BTC-USD',
    name: 'Bitcoin',
    asset_class: 'crypto',
    region: 'global',
    history_from: '2015-01-01',
  },
  {
    symbol: 'ETH-USD',
    name: 'Ethereum',
    asset_class: 'crypto',
    region: 'global',
    history_from: '2017-01-01',
  },
]

function mockResult(symbol: string, name: string): RoiCalculateResult {
  return {
    symbol,
    name,
    asset_class: 'crypto',
    region: 'global',
    strategy: 'buy_hold',
    amount: 10000,
    invested: 10000,
    final_value: 20000,
    profit: 10000,
    roi_pct: 100,
    cagr_pct: 10,
    max_drawdown_pct: 20,
    years: 10,
    data_start: '2015-01-01',
    data_end: '2025-01-01',
    bars: 120,
    cycle_source: 'test',
    equity_curve: [],
    trades: [],
    price_series: [],
    btc_cycle_aths: [],
    disclaimer: 'test',
  }
}

function renderPage(initialEntry = '/kalkulator?mode=backtest&symbol=BTC-USD') {
  return render(
    <LocaleProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/kalkulator" element={<RoiCalculatorPage />} />
        </Routes>
      </MemoryRouter>
    </LocaleProvider>,
  )
}

async function waitForRoiForm() {
  await screen.findByRole('combobox')
}

describe('RoiCalculatorPage symbol sync', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    Element.prototype.scrollIntoView = vi.fn()
    vi.mocked(api.fetchRoiAssets).mockResolvedValue(mockAssets)
    vi.mocked(api.calculateRoi).mockImplementation(async ({ symbol }) => {
      if (symbol === 'ETH-USD') return mockResult('ETH-USD', 'Ethereum')
      return mockResult('BTC-USD', 'Bitcoin')
    })
  })

  it('recalculates backtest results when asset changes in the form', async () => {
    renderPage()

    expect(await screen.findByText('Bitcoin', { selector: 'strong' })).toBeTruthy()
    await waitFor(() => expect(api.calculateRoi).toHaveBeenCalledWith(expect.objectContaining({ symbol: 'BTC-USD' })))

    const assetSelect = screen.getByRole('combobox')
    fireEvent.change(assetSelect, { target: { value: 'ETH-USD' } })

    await waitFor(() => expect(api.calculateRoi).toHaveBeenCalledWith(expect.objectContaining({ symbol: 'ETH-USD' })))
    expect(await screen.findByText('Ethereum', { selector: 'strong' })).toBeTruthy()
    expect(screen.queryByText('Bitcoin', { selector: 'strong' })).toBeNull()
  })

  it('recalculates when URL symbol changes after initial backtest load', async () => {
    const { unmount } = renderPage()

    await waitFor(() => expect(api.calculateRoi).toHaveBeenCalledWith(expect.objectContaining({ symbol: 'BTC-USD' })))
    unmount()
    vi.mocked(api.calculateRoi).mockClear()

    renderPage('/kalkulator?mode=backtest&symbol=ETH-USD')

    await waitFor(() => expect(api.calculateRoi).toHaveBeenCalledWith(expect.objectContaining({ symbol: 'ETH-USD' })))
    expect(await screen.findByText('Ethereum', { selector: 'strong' })).toBeTruthy()
  })
})

describe('RoiCalculatorPage numeric inputs', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    Element.prototype.scrollIntoView = vi.fn()
    vi.mocked(api.fetchRoiAssets).mockResolvedValue(mockAssets)
    vi.mocked(api.calculateRoi).mockImplementation(async ({ symbol }) => mockResult(symbol, 'Bitcoin'))
  })

  it('shows empty optional monthly field and allows typing without forcing zero', async () => {
    renderPage('/kalkulator?mode=forward')
    await waitForRoiForm()

    const monthly = (await screen.findByLabelText('Monthly add-on (USD, optional)')) as HTMLInputElement
    expect(monthly.value).toBe('')

    fireEvent.focus(monthly)
    fireEvent.change(monthly, { target: { value: '250' } })
    expect(monthly.value).toBe('250')

    fireEvent.blur(monthly)
    expect(monthly.value).toBe('250')
  })

  it('clears optional monthly field back to empty on blur', async () => {
    renderPage('/kalkulator?mode=forward')
    await waitForRoiForm()

    const monthly = (await screen.findByLabelText('Monthly add-on (USD, optional)')) as HTMLInputElement
    fireEvent.focus(monthly)
    fireEvent.change(monthly, { target: { value: '500' } })
    fireEvent.blur(monthly)
    expect(monthly.value).toBe('500')

    fireEvent.focus(monthly)
    fireEvent.change(monthly, { target: { value: '' } })
    fireEvent.blur(monthly)
    expect(monthly.value).toBe('')
  })

  it('lets amount field be cleared while editing and restores on empty blur', async () => {
    renderPage('/kalkulator?mode=forward')
    await waitForRoiForm()

    const amount = (await screen.findByLabelText('Investing today (USD)')) as HTMLInputElement
    expect(amount.value).toBe('10000')

    fireEvent.focus(amount)
    fireEvent.change(amount, { target: { value: '' } })
    expect(amount.value).toBe('')

    fireEvent.blur(amount)
    expect(amount.value).toBe('10000')
  })

  it('commits amount edits on blur', async () => {
    renderPage('/kalkulator?mode=forward')
    await waitForRoiForm()

    const amount = (await screen.findByLabelText('Investing today (USD)')) as HTMLInputElement
    fireEvent.focus(amount)
    fireEvent.change(amount, { target: { value: '25000' } })
    fireEvent.blur(amount)
    expect(amount.value).toBe('25000')
  })
})
