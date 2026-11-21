import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api'
import { LocaleProvider } from '../context/LocaleContext'
import type { MacroNewsItem } from '../types'
import { MarketHeatSection, selectMarketHeat } from './MarketHeatSection'

function item(over: Partial<MacroNewsItem> = {}): MacroNewsItem {
  return {
    id: over.id ?? Math.random().toString(36).slice(2),
    title: over.title ?? 'Tytuł',
    summary: over.summary ?? 'Streszczenie',
    url: over.url ?? 'https://example.com/a',
    image_url: null,
    source_image_url: null,
    source: over.source ?? 'Reuters',
    category: over.category ?? 'fed',
    impact: over.impact ?? 'high',
    published_at: over.published_at ?? '2026-11-20T10:00:00Z',
    is_curated: over.is_curated ?? false,
    age_minutes: null,
  }
}

function feed(items: MacroNewsItem[]): import('../types').MacroNewsFeed {
  return {
    items,
    fetched_at: '2026-11-20T10:05:00Z',
    counts: {},
    sources_count: 1,
    poll_interval_seconds: 60,
    fresh_count_1h: items.length,
  }
}

describe('selectMarketHeat', () => {
  it('keeps only high-impact or curated items and drops the rest', () => {
    const picked = selectMarketHeat([
      item({ id: 'h', impact: 'high' }),
      item({ id: 'c', impact: 'low', is_curated: true }),
      item({ id: 'lo', impact: 'low', is_curated: false }),
      item({ id: 'med', impact: 'medium', is_curated: false }),
    ])
    expect(picked.map((p) => p.id)).toEqual(['h', 'c'])
  })

  it('sorts newest first, dedupes and caps at five', () => {
    const picked = selectMarketHeat([
      item({ id: 'old', published_at: '2026-11-01T00:00:00Z' }),
      item({ id: 'new', published_at: '2026-11-20T00:00:00Z' }),
      item({ id: 'new' }), // duplicate id dropped
      item({ id: 'a', published_at: '2026-11-19T00:00:00Z' }),
      item({ id: 'b', published_at: '2026-11-18T00:00:00Z' }),
      item({ id: 'c', published_at: '2026-11-17T00:00:00Z' }),
      item({ id: 'd', published_at: '2026-11-16T00:00:00Z' }),
    ])
    expect(picked).toHaveLength(5)
    expect(picked[0].id).toBe('new')
  })
})

function renderSection() {
  return render(
    <LocaleProvider>
      <MarketHeatSection />
    </LocaleProvider>,
  )
}

describe('MarketHeatSection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders verified items with both labelled blocks and a source link', async () => {
    vi.spyOn(api, 'fetchMacroNews').mockResolvedValue(
      feed([item({ id: 'x', title: 'Fed utrzymuje stopy', source: 'Reuters', url: 'https://r.test/x' })]),
    )

    renderSection()

    expect(await screen.findByText('Fed utrzymuje stopy')).toBeTruthy()
    expect(screen.getByText('Co się stało')).toBeTruthy()
    expect(screen.getByText('Dlaczego ważne dla rynku')).toBeTruthy()
    const link = screen.getByRole('link', { name: /Reuters/ })
    expect(link.getAttribute('href')).toBe('https://r.test/x')
  })

  it('shows the empty state when the feed has no high-stakes items', async () => {
    vi.spyOn(api, 'fetchMacroNews').mockResolvedValue(feed([item({ id: 'lo', impact: 'low', is_curated: false })]))

    renderSection()

    await waitFor(() =>
      expect(
        screen.getByText(/brak zweryfikowanych tematów o dużym znaczeniu dla rynku/i),
      ).toBeTruthy(),
    )
  })
})
