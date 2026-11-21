import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api'
import { LocaleProvider } from '../context/LocaleContext'
import { LOCALE_STORAGE_KEY } from '../i18n'
import type { BitcoinCycleStatus, RoiShowcaseResult } from '../types'
import { CycleCardBitcoin } from './CycleCardBitcoin'
import { InvestmentShowcase } from './InvestmentShowcase'

vi.mock('../api', () => ({
  fetchRoiShowcase: vi.fn(),
}))
vi.mock('./IntramonthSeasonalityPanel', () => ({ IntramonthSeasonalityPanel: () => null }))
vi.mock('./MonthPumpSnippet', () => ({ MonthPumpSnippet: () => null }))

function wrap(ui: React.ReactNode) {
  return render(
    <LocaleProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </LocaleProvider>,
  )
}

describe('live market data on the home page', () => {
  beforeEach(() => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    vi.mocked(api.fetchRoiShowcase).mockReset()
  })

  it('shows "brak danych" instead of numbers when a backtest card has no real data', async () => {
    const payload: RoiShowcaseResult = {
      amount: 10000,
      years: 10,
      start: '2016-11-21',
      end: '2026-11-21',
      strategy: 'cycle',
      disclaimer: '',
      source: 'Yahoo Finance',
      updated_at: '2026-11-21T05:50:00Z',
      refresh_seconds: 600,
      cards: [
        {
          id: 'sp500',
          featured: false,
          symbol: '^GSPC',
          name: 'S&P 500',
          strategy: 'cycle',
          available: true,
          stale: false,
          final_value: 22820.52,
          profit: 12820.52,
          roi_pct: 128.21,
          data_start: '2016-11-21',
          data_end: '2026-11-20',
          start_price: 2198.18,
          end_price: 6910.39,
          source: 'Yahoo Finance',
          updated_at: '2026-11-21T05:50:00Z',
          buy_hold: { final_value: 31436.87, roi_pct: 214.37, cagr_pct: 12.1 },
        },
        {
          id: 'gold',
          featured: false,
          symbol: 'GC=F',
          name: 'GC=F',
          strategy: 'cycle',
          available: false,
          stale: true,
          error: 'brak danych',
          source: 'Yahoo Finance',
          updated_at: null,
        },
      ],
    }
    vi.mocked(api.fetchRoiShowcase).mockResolvedValue(payload)
    wrap(<InvestmentShowcase />)
    const gold = await screen.findByTestId('showcase-card-gold')
    expect(gold.textContent).toContain('brak danych')
    expect(gold.textContent).not.toMatch(/USD/)
    const spx = screen.getByTestId('showcase-card-sp500')
    expect(spx.textContent).toContain('+128.2%')
    expect(spx.textContent).toContain('214.4')
    expect(spx.textContent).toContain('Źródło: Yahoo Finance')
    expect(spx.textContent).toContain('aktualizacja')
  })

  it('shows "brak danych" when the showcase endpoint fails and nothing real was loaded', async () => {
    vi.mocked(api.fetchRoiShowcase).mockRejectedValue(new Error('502'))
    wrap(<InvestmentShowcase />)
    await waitFor(() => expect(screen.getByText(/brak danych/)).toBeTruthy())
  })

  it('BTC cycle card names its source, update time and real-price confirmation', () => {
    const cycle: BitcoinCycleStatus = {
      last_ath_date: '2025-10-06',
      last_ath_price: 126080,
      current_price: 55869,
      days_since_ath: 411,
      bear_phase_end_day: 364,
      bull_phase_end_day: 1428,
      phase: 'accumulation',
      model_phase: 'bull',
      phase_progress_pct: 4.4,
      days_remaining_in_phase: 1017,
      signal: 'watch',
      rationale: '',
      drawdown_from_ath_pct: 55.69,
      cycle_low_price: 55659.47,
      cycle_low_date: '2026-11-21',
      rebound_from_low_pct: 0.38,
      price_confirmed: false,
      price_source: 'CoinGecko',
      price_updated_at: '2026-11-21T05:52:00Z',
      ath_source: 'CoinGecko',
      stale: false,
    }
    wrap(<CycleCardBitcoin cycle={cycle} />)
    const stamp = screen.getByTestId('data-stamp')
    expect(stamp.textContent).toContain('Źródło: CoinGecko')
    expect(stamp.textContent).toContain('aktualizacja')
    expect(document.body.textContent).toContain('Akumulacja')
    expect(document.body.textContent).toContain('1064d')
    expect(document.body.textContent).toContain('−55.7%')
  })
})
