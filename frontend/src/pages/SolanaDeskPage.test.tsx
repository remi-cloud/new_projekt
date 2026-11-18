import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/LocaleContext'
import { LOCALE_STORAGE_KEY } from '../i18n'
import { SolanaDeskPage } from './SolanaDeskPage'

vi.mock('../lib/solanaDeskApi', () => ({
  solanaCsvUrl: '/api/solana/trades.csv',
  fetchSolanaStatus: vi.fn(async () => ({
    mode: 'paper',
    running: true,
    kill_switch: false,
    real_trading_flag: false,
    wallet_configured: false,
    real_trading_active: false,
    lock_reason: 'Handel realny jest wyłączony.',
    cash_sol: 1,
    equity_sol: 1,
    equity_usd: 140,
    sol_usd: 140,
    net_pnl_sol: 0,
    realized_pnl_sol: 0,
    fees_sol: 0,
    win_rate: 0.5,
    closed_trades: 2,
    wins: 1,
    open_positions: 0,
    max_drawdown: 0.04,
    last_tick_at: '2026-11-18T07:00:00Z',
    last_error: '',
    worker_online: true,
    settings: { starting_sol: 1, position_sol: 0.05, max_per_trade_sol: 0.1, daily_loss_sol: 0.2, stop_pct: 0.06 },
    agents: {
      scout: { seen: 4, note: 'Kandydaci w tym obiegu: 4.' },
      checker: { passed: 1, rejected: 3, note: 'Odrzucony: aktywne uprawnienie mint' },
      sniper: { entries: 1, note: 'Papierowe wejście.' },
      exit: { exits: 1, note: 'Stop po kolejnej cenie.' },
    },
    positions: [],
    report: {
      title: 'Raport dzienny 2026-11-18 UTC',
      pnl_sol: -0.01,
      fees_sol: 0.002,
      closed_trades: 2,
      win_rate: 0.5,
      max_drawdown: 0.04,
      note: 'Symulacja papierowa.',
    },
  })),
  fetchSolanaJournal: vi.fn(async () => ({
    trades: [
      {
        id: 1,
        opened_at: '2026-11-18T07:00:00Z',
        closed_at: '2026-11-18T07:05:00Z',
        mint: 'Mint111pump',
        symbol: 'FLOW',
        status: 'closed',
        entry_price: 0.001,
        exit_price: 0.0004,
        entry_fee_sol: 0.001,
        exit_fee_sol: 0.0004,
        entry_slippage: 0.01,
        exit_slippage: 0.02,
        pnl_sol: -0.02,
        entry_reason: 'Checker przepuścił',
        exit_reason: 'stop -6% — wypełnienie po kolejnej cenie',
        mode: 'paper',
        solscan_url: null,
      },
    ],
    events: [{ id: 7, ts: '2026-11-18T07:05:00Z', agent: 'exit', mint: 'Mint111pump', symbol: 'FLOW', message: 'Stop po luce.' }],
  })),
  postSolanaControl: vi.fn(),
  postSolanaSettings: vi.fn(),
}))

describe('Solana Desk', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
  })

  it('pokazuje papierowe statystyki i blokuje sterowanie gościowi', async () => {
    render(
      <LocaleProvider>
        <MemoryRouter>
          <SolanaDeskPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Solana Desk' })).toBeTruthy()
    expect(screen.getByText(/Tryb papierowy/)).toBeTruthy()
    expect(screen.getAllByText(/FLOW/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Stop po luce/)).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Start' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Zapisz' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByRole('link', { name: 'Eksport CSV' })).toBeTruthy()
  })

  it('po tokenie biurka puszcza start', async () => {
    sessionStorage.setItem('cyclical-desk-token', 'pytest-desk')
    render(
      <LocaleProvider>
        <MemoryRouter>
          <SolanaDeskPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    const start = await screen.findByRole('button', { name: 'Start' })
    expect((start as HTMLButtonElement).disabled).toBe(false)
  })
})
