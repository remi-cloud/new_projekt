import { useEffect, useMemo, useState } from 'react'
import { fetchMacroNews } from '../api'
import { useLocale } from '../context/LocaleContext'
import type { MacroNewsItem } from '../types'
import type { TranslationPath } from '../i18n'

const MAX_ITEMS = 5
const KNOWN_CATEGORIES = new Set(['fed', 'usa', 'macro', 'global', 'musk', 'crypto'])

/**
 * Pick the market-relevant, high-stakes items from the macro-news feed.
 * Only verified feed items are used — nothing is invented here. We keep the
 * high-impact and editorially-curated entries, drop duplicates and social
 * noise, and surface the freshest few.
 */
export function selectMarketHeat(items: MacroNewsItem[]): MacroNewsItem[] {
  const seen = new Set<string>()
  return items
    .filter((it) => (it.impact === 'high' || it.is_curated) && Boolean(it.title))
    .filter((it) => {
      const key = (it.id || it.title).trim()
      if (!key || seen.has(key)) return false
      seen.add(key)
      return true
    })
    .sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime())
    .slice(0, MAX_ITEMS)
}

function whyKey(category: string): TranslationPath {
  const cat = KNOWN_CATEGORIES.has(category) ? category : 'default'
  return `marketHeat.why.${cat}` as TranslationPath
}

export function MarketHeatSection() {
  const { t, dateLocale, locale } = useLocale()
  const [items, setItems] = useState<MacroNewsItem[] | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  useEffect(() => {
    let active = true
    fetchMacroNews(undefined, 100, locale)
      .then((feed) => {
        if (active) setItems(selectMarketHeat(feed.items ?? []))
      })
      .catch(() => {
        if (active) setItems([])
      })
    return () => {
      active = false
    }
  }, [locale])

  const formatDate = useMemo(
    () => (iso: string) => {
      const d = new Date(iso)
      if (Number.isNaN(d.getTime())) return ''
      return d.toLocaleDateString(dateLocale, { day: '2-digit', month: 'short', year: 'numeric' })
    },
    [dateLocale],
  )

  // Loading: render nothing (keeps the guest landing clean until data arrives).
  if (items === null) return null

  return (
    <section className="market-heat" aria-labelledby="market-heat-title">
      <div className="section-header">
        <h2 id="market-heat-title" className="section-title">
          {t('marketHeat.title')}
        </h2>
        <span className="market-heat-subtitle">{t('marketHeat.subtitle')}</span>
      </div>

      {items.length === 0 ? (
        <p className="market-heat-empty">{t('marketHeat.empty')}</p>
      ) : (
        <div className="market-heat-grid">
          {items.map((item) => {
            const isOpen = Boolean(expanded[item.id])
            const summary = item.summary?.trim()
            return (
              <article key={item.id} className="market-heat-card">
                <header className="market-heat-card-head">
                  <span className="market-heat-date">{formatDate(item.published_at)}</span>
                  {item.impact === 'high' && <span className="market-heat-badge">{t('marketHeat.title')}</span>}
                </header>
                <h3 className="market-heat-headline">{item.title}</h3>

                <div className="market-heat-block">
                  <span className="market-heat-label">{t('marketHeat.whatHappened')}</span>
                  <p className={isOpen ? 'market-heat-text' : 'market-heat-text market-heat-clamp'}>
                    {summary || item.title}
                  </p>
                </div>

                <div className="market-heat-block">
                  <span className="market-heat-label">{t('marketHeat.whyMatters')}</span>
                  <p className="market-heat-text">{t(whyKey(item.category))}</p>
                </div>

                <footer className="market-heat-foot">
                  {item.url && (
                    <a
                      className="market-heat-source"
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {t('marketHeat.source')}: {item.source}
                    </a>
                  )}
                  {summary && summary.length > 140 && (
                    <button
                      type="button"
                      className="link-btn tap-target"
                      onClick={() => setExpanded((prev) => ({ ...prev, [item.id]: !isOpen }))}
                    >
                      {isOpen ? t('marketHeat.collapse') : t('marketHeat.readMore')}
                    </button>
                  )}
                </footer>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
