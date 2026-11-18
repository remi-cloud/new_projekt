import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { Layout } from '../components/Layout'
import { LocaleProvider } from '../context/LocaleContext'
import { NAV_SECTIONS } from '../constants'
import { LOCALE_STORAGE_KEY } from '../i18n'
import { AiHackingPage } from '../pages/AiHackingPage'
import { RadarPage } from '../pages/RadarPage'

function renderLayout() {
  localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
  return render(
    <LocaleProvider>
      <MemoryRouter initialEntries={['/dashboard']}>
        <Layout />
      </MemoryRouter>
    </LocaleProvider>,
  )
}

describe('menu routes', () => {
  it('renders a link for every sidebar destination and keeps AI first', () => {
    renderLayout()
    const hrefs = screen.getAllByRole('link').map((link) => link.getAttribute('href'))
    for (const section of NAV_SECTIONS) {
      for (const item of section.items) {
        expect(hrefs).toContain(item.path)
      }
    }
    expect(hrefs.indexOf('/ai-hacking')).toBeLessThan(hrefs.indexOf('/dashboard'))
    expect(hrefs.indexOf('/radar')).toBeLessThan(hrefs.indexOf('/dashboard'))
    expect(screen.getAllByRole('link', { name: 'AI i hacking' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: 'Radar' }).length).toBeGreaterThan(0)
  })
})

describe('AI security pages', () => {
  it('renders the hacking desk from the academy payload', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            eyebrow: 'Edukacja',
            title: 'AI i hacking',
            lead: 'Obrona konta.',
            disclaimer: 'Tylko obrona.',
            parts: [{ id: 'security', title: 'Bezpieczeństwo', lead: 'Higiena.', sections: [] }],
          }),
          { status: 200 },
        ),
      ),
    )
    render(
      <LocaleProvider>
        <MemoryRouter>
          <AiHackingPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'AI i hacking' })).toBeTruthy()
    expect(await screen.findByText('Bezpieczeństwo')).toBeTruthy()
    vi.unstubAllGlobals()
  })

  it('renders the scam radar', () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    render(
      <LocaleProvider>
        <MemoryRouter>
          <RadarPage />
        </MemoryRouter>
      </LocaleProvider>,
    )
    expect(screen.getByRole('heading', { name: 'Radar oszustw' })).toBeTruthy()
  })
})
