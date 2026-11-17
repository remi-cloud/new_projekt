import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/LocaleContext'
import { LOCALE_STORAGE_KEY } from '../i18n'
import { DeskLoginPage } from './DeskLoginPage'

describe('Desk login', () => {
  it('stores the token in session memory after a successful check', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
    sessionStorage.clear()
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/desk/status')) {
        return new Response(JSON.stringify({ configured: true }), { status: 200 })
      }
      const body = JSON.parse(String(init?.body || '{}')) as { token?: string }
      const ok = body.token === 'sekret-test'
      return new Response(JSON.stringify(ok ? { ok: true } : { detail: 'Zły token biurka.' }), {
        status: ok ? 200 : 401,
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    render(
      <LocaleProvider>
        <DeskLoginPage />
      </LocaleProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'Logowanie biurka' })).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Token biurka'), { target: { value: 'sekret-test' } })
    fireEvent.click(screen.getByRole('button', { name: 'Wejdź' }))
    expect(await screen.findByText('Zalogowano. Token jest tylko w tej sesji przeglądarki.')).toBeTruthy()
    expect(sessionStorage.getItem('cyclical-desk-token')).toBe('sekret-test')
    vi.unstubAllGlobals()
  })
})
