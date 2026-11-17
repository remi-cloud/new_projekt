import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { LocaleProvider } from '../context/LocaleContext'
import { LOCALE_STORAGE_KEY } from '../i18n'
import { Layout } from './Layout'

function renderAt(path: string) {
  localStorage.setItem(LOCALE_STORAGE_KEY, 'pl')
  return render(
    <LocaleProvider>
      <MemoryRouter initialEntries={[path]}>
        <Layout />
      </MemoryRouter>
    </LocaleProvider>,
  )
}

describe('Layout navigation', () => {
  it('marks the current section link as active', () => {
    renderAt('/okazje')
    const current = screen.getAllByRole('link', { name: 'Okazje' }).find((link) => link.getAttribute('aria-current') === 'page')
    expect(current).toBeTruthy()
    expect(current?.className).toContain('active')
  })

  it('names the desk symbol and a missing page, not the home title', () => {
    renderAt('/pozycja/BTC-USD')
    expect(screen.getAllByRole('heading', { name: 'BTC-USD' }).length).toBeGreaterThan(0)
    expect(document.title).toContain('BTC-USD')
    expect(screen.queryByRole('heading', { name: 'Start' })).toBeNull()
  })

  it('uses the symbol on a superokazje deep link', () => {
    renderAt('/superokazje/ETH-USD')
    expect(screen.getAllByRole('heading', { name: 'ETH-USD' }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('heading', { name: 'Rynki' })).toBeNull()
  })

  it('titles an unknown route as not found', () => {
    renderAt('/nie-ma-takiej-strony')
    expect(screen.getAllByRole('heading', { name: 'Strona nie znaleziona' }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('heading', { name: 'Start' })).toBeNull()
  })

  it('toggles the mobile menu', () => {
    renderAt('/dashboard')
    expect(screen.queryByRole('navigation', { name: 'Menu' })).toBeNull()
    const toggle = screen.getAllByRole('button', { name: 'Menu' })[0]
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByRole('navigation', { name: 'Menu' })).toBeTruthy()
    const closeButtons = screen.getAllByRole('button', { name: 'Zamknij' })
    expect(closeButtons).toHaveLength(1)
    expect(closeButtons[0].className).toContain('mobile-menu-btn')
    expect(closeButtons[0].closest('.bottom-nav')).toBeNull()
    const bottomMenu = screen.getAllByRole('button', { name: 'Menu' })
    expect(bottomMenu).toHaveLength(1)
    expect(bottomMenu[0].className).toContain('active')
    expect(bottomMenu[0].closest('.bottom-nav')).toBeTruthy()
    fireEvent.click(closeButtons[0])
    expect(screen.queryByRole('navigation', { name: 'Menu' })).toBeNull()
  })
})
