import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/LocaleContext'
import { LOCALE_STORAGE_KEY } from '../i18n'
import fixture from '../test/fixtures/terminal.json'
import { SolanaDeskPage } from './SolanaDeskPage'

const payload = fixture

vi.mock('../lib/solanaDeskApi', async () => {
  const loaded = (await import('../test/fixtures/terminal.json')).default
  return {
  solanaCsvUrl: '/api/solana/trades.csv',
  fetchSolanaTerminal: vi.fn(async () => structuredClone(loaded)),
  fetchSolanaStatus: vi.fn(async () => ({
    running: true,
    kill_switch: false,
    armed: false,
    settings: { risk_per_trade_pct: 0.015, position_sol: 0.05 },
    closed_trades: 1,
    open_positions: 0,
  })),
  fetchSolanaJournal: vi.fn(async () => ({ trades: [], events: [] })),
  fetchSolanaDecisions: vi.fn(async () => ({ decisions: [] })),
  fetchSolanaLessons: vi.fn(async () => ({ lessons: [] })),
  fetchSolanaSelfTest: vi.fn(async () => ({ ok: null, agents: {} })),
  postSolanaArm: vi.fn(),
  postSolanaControl: vi.fn(),
  postSolanaSettings: vi.fn(),
  postSolanaSelfTest: vi.fn(),
  }
})

describe('Grok Bot Terminal', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    class FakeSource {
      addEventListener() {}
      close() {}
      onerror: (() => void) | null = null
    }
    vi.stubGlobal('EventSource', FakeSource)
  })

  it('renders the real terminal payload and refuses illustrative copy', async () => {
    render(
      <LocaleProvider>
        <MemoryRouter>
          <SolanaDeskPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    expect(await screen.findByText('Grok Bot')).toBeTruthy()
    expect(screen.getByText('Terminal')).toBeTruthy()
    expect(screen.getByText('AGENTS')).toBeTruthy()
    expect(screen.getByText('paper · live')).toBeTruthy()
    expect(screen.getByText('paper · real quotes')).toBeTruthy()
    expect(screen.getByText(/every trade gets a reason/)).toBeTruthy()
    for (const name of ['SCANNER', 'RUG CHECK', 'SIZER', 'EXECUTOR', 'LOGGER', 'EQUITY', 'YOU']) {
      expect(screen.getAllByText(name).length).toBeGreaterThan(0)
    }
    expect(document.body.textContent || '').not.toMatch(/illustrative/i)
    const clock = screen.getByTestId('gbt-clock').textContent || ''
    const expected = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Europe/Oslo',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(new Date())
    expect(clock.slice(0, 5)).toBe(expected.slice(0, 5))
  })

  it('applies an SSE snapshot to the action chip', async () => {
    const box: { fn: ((event: MessageEvent) => void) | null } = { fn: null }
    class FakeSource {
      addEventListener(type: string, fn: (event: MessageEvent) => void) {
        if (type === 'snapshot') box.fn = fn
      }
      close() {}
      onerror: (() => void) | null = null
    }
    vi.stubGlobal('EventSource', FakeSource)
    render(
      <LocaleProvider>
        <MemoryRouter>
          <SolanaDeskPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    await screen.findByText('Grok Bot')
    const next = structuredClone(payload)
    next.header.current_action = 'EXECUTOR · ENTERED $TEST'
    next.header.trades = payload.header.trades + 3
    box.fn?.({ data: JSON.stringify(next) } as MessageEvent)
    expect(await screen.findByText('EXECUTOR · ENTERED $TEST')).toBeTruthy()
  })

  it('keeps desk controls locked for a guest', async () => {
    render(
      <LocaleProvider>
        <MemoryRouter>
          <SolanaDeskPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    const open = await screen.findByRole('button', { name: 'Sterowanie' })
    open.click()
    const start = await screen.findByRole('button', { name: 'Start' })
    expect((start as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Zapisz' }) as HTMLButtonElement).disabled).toBe(true)
  })
})
