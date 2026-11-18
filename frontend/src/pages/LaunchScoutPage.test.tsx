import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/LocaleContext'
import { LOCALE_STORAGE_KEY } from '../i18n'
import { LaunchScoutPage } from './LaunchScoutPage'

vi.mock('../api', () => ({
  fetchLaunchStatus: vi.fn(async () => ({
    enabled: true,
    counts: { seed: 1, all: 1 },
  })),
  fetchLaunchCandidates: vi.fn(async () => ({
    candidates: [{ symbol: 'SEED', tier: 'seed', chain: 'solana', market_cap: 200 }],
  })),
}))

describe('Launch Scout route', () => {
  it('shows the scout desk instead of the security page', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    render(
      <LocaleProvider>
        <LaunchScoutPage />
      </LocaleProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Launch Scout' })).toBeTruthy()
    expect(await screen.findByText('SEED')).toBeTruthy()
    expect(screen.queryByText('AI i hacking')).toBeNull()
  })

  it('retries a failed load from the button', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    const api = await import('../api')
    vi.mocked(api.fetchLaunchStatus).mockRejectedValueOnce(new Error('down'))
    vi.mocked(api.fetchLaunchCandidates).mockRejectedValueOnce(new Error('down'))
    render(
      <LocaleProvider>
        <LaunchScoutPage />
      </LocaleProvider>,
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Spróbuj ponownie' }))
    expect(await screen.findByText('SEED')).toBeTruthy()
  })
})