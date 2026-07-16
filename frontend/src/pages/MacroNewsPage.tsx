import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchMacroNews, refreshMacroNews } from '../api'
import { MacroCalendarTab } from '../components/MacroCalendarTab'
import { GrowthFunnelStrip } from '../components/GrowthFunnelStrip'
import { ErrorState } from '../components/Loading'
import { NewsShareMenu } from '../components/NewsShareMenu'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'
import type { TranslationPath } from '../i18n'
import { MacroNewsCategory, MacroNewsFeed, MacroNewsItem } from '../types'

type ViewMode = 'news' | 'calendar'
type TabId = 'all' | MacroNewsCategory

const NEWS_TAB_IDS: TabId[] = ['all', 'musk', 'fed', 'usa', 'macro', 'global']

function formatTime(item: MacroNewsItem, t: (p: TranslationPath, v?: Record<string, string | number>) => string, dateLocale: string): string {
  if (item.age_minutes != null) {
    if (item.age_minutes < 1) return t('macro.now')
    if (item.age_minutes < 60) return t('macro.timeAgoMin', { n: item.age_minutes })
    const hrs = Math.floor(item.age_minutes / 60)
    if (hrs < 48) return t('macro.timeAgoHr', { n: hrs })
  }
  const d = new Date(item.published_at)
  if (Number.isNaN(d.getTime())) return ''
  const diff = Date.now() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('macro.now')
  if (mins < 60) return t('macro.timeAgoMin', { n: mins })
  const hrs = Math.floor(mins / 60)
  if (hrs < 48) return t('macro.timeAgoHr', { n: hrs })
  return d.toLocaleString(dateLocale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function isBreaking(item: MacroNewsItem): boolean {
  return !item.is_curated && (item.age_minutes ?? 999) <= 5
}

function NewsCard({
  item,
  index,
  t,
  dateLocale,
}: {
  item: MacroNewsItem
  index: number
  t: (p: TranslationPath, v?: Record<string, string | number>) => string
  dateLocale: string
}) {
  const breaking = isBreaking(item)
  const style = { animationDelay: `${Math.min(index * 0.05, 0.6)}s` } as const
  const cardClass = `macro-news-card macro-news-card-enter ${breaking ? 'macro-news-card-breaking' : ''}`

  const body = (
    <>
      <div className="macro-news-card-head">
        <span className={`macro-news-cat macro-news-cat-${item.category}`}>
          {t(`macro.category.${item.category}`)}
        </span>
        {breaking && <span className="macro-news-live">{t('macro.now')}</span>}
        {item.impact === 'high' && <span className="macro-news-impact">{t('macro.highImpact')}</span>}
      </div>
      {item.image_url && (
        <div className="macro-news-image-wrap">
          <img
            className="macro-news-image"
            src={item.image_url}
            alt=""
            loading="lazy"
            decoding="async"
          />
        </div>
      )}
      <h4 className="macro-news-title">{item.title}</h4>
      {item.summary && <p className="macro-news-summary">{item.summary}</p>}
    </>
  )

  return (
    <article className={cardClass} style={style}>
      {item.url ? (
        <a href={item.url} target="_blank" rel="noopener noreferrer" className="macro-news-card-link tap-target">
          {body}
        </a>
      ) : (
        <div className="macro-news-card-body">{body}</div>
      )}
      <div className="macro-news-card-foot">
        <div className="macro-news-meta">
          <span>{item.source}</span>
          <span>{formatTime(item, t, dateLocale)}</span>
        </div>
        <NewsShareMenu title={item.title} url={item.url} source={item.source} />
      </div>
    </article>
  )
}

export function MacroNewsPage() {
  const { t, dateLocale, locale } = useLocale()
  const [view, setView] = useState<ViewMode>('news')
  const [tab, setTab] = useState<TabId>('all')
  const [feed, setFeed] = useState<MacroNewsFeed | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const tabRef = useRef(tab)
  const viewRef = useRef(view)
  tabRef.current = tab
  viewRef.current = view

  const load = useCallback(async (category: TabId, silent = false) => {
    if (!silent) setError(null)
    try {
      const data = await fetchMacroNews(category === 'all' ? undefined : category, 100, locale)
      setFeed(data)
    } catch {
      if (!silent) setError(t('macro.errors.fetchNews'))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [t, locale])

  const { connected } = useLiveFeed((event) => {
    if (event.type === 'macro_news_tick' || event.type === 'macro_news' || event.type === 'macro_news_image') {
      if (viewRef.current === 'news') void load(tabRef.current, true)
    }
  })

  useEffect(() => {
    if (view !== 'news') return
    setLoading(true)
    void load(tab)
  }, [tab, load, view])

  useEffect(() => {
    if (view !== 'news') return
    if (connected) return
    const pollMs = (feed?.poll_interval_seconds ?? 120) * 1000
    const id = window.setInterval(() => void load(tabRef.current, true), pollMs)
    return () => window.clearInterval(id)
  }, [load, feed?.poll_interval_seconds, view, connected])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const data = await refreshMacroNews(locale)
      setFeed(data)
      await load(tab, true)
    } catch {
      alert(t('macro.errors.refresh'))
    } finally {
      setRefreshing(false)
    }
  }

  const counts = feed?.counts ?? {}
  const pollSec = feed?.poll_interval_seconds ?? 120

  if (view === 'news' && loading && !feed) {
    return <div className="page-loading macro-page-loading">{t('macro.loadingNews')}</div>
  }
  if (view === 'news' && error && !feed) {
    return <ErrorState message={error} onRetry={() => load(tab)} />
  }

  return (
    <div className="macro-news-page institutional-page macro-news-page-live">
      <div className="macro-news-bg" aria-hidden>
        <span className="macro-orb macro-orb-1" />
        <span className="macro-orb macro-orb-2" />
        <span className="macro-orb macro-orb-3" />
        <span className="macro-scan-line" />
      </div>

      <header className="page-intro macro-hero-enter">
        <span className="page-eyebrow macro-eyebrow-glow">{t('macro.eyebrow')}</span>
        <h2 className="page-headline macro-headline-shine">{t('macro.headline')}</h2>
        <p className="page-lead">
          {t('macro.lead')} <strong>{t('macro.leadHighlight')}</strong>.
        </p>
      </header>

      <div className="macro-news-status-bar macro-status-enter">
        <span className={`macro-news-live-pill ${connected ? 'on' : ''}`}>
          <span className="macro-news-live-dot" />
          {connected ? t('macro.live') : t('macro.connecting')}
        </span>
        {view === 'news' && feed && feed.fresh_count_1h > 0 && (
          <span className="macro-news-fresh-badge">
            {t('macro.freshLastHour', { count: feed.fresh_count_1h })}
          </span>
        )}
        <span className="macro-news-poll-hint">{t('macro.refreshEvery', { sec: pollSec })}</span>
      </div>

      <div className="macro-view-tabs macro-tabs-enter" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={view === 'news'}
          className={`macro-view-tab ${view === 'news' ? 'active' : ''}`}
          onClick={() => setView('news')}
        >
          {t('macro.tabNews')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'calendar'}
          className={`macro-view-tab macro-view-tab-calendar ${view === 'calendar' ? 'active' : ''}`}
          onClick={() => setView('calendar')}
        >
          {t('macro.tabCalendar')}
        </button>
      </div>

      <div className={`macro-view-panel ${view === 'calendar' ? 'macro-view-calendar' : 'macro-view-news'}`}>
        {view === 'calendar' ? (
          <MacroCalendarTab />
        ) : (
          <>
            <div className="macro-news-toolbar">
              <div className="macro-news-tabs" role="tablist">
                {NEWS_TAB_IDS.map((id) => (
                  <button
                    key={id}
                    type="button"
                    role="tab"
                    aria-selected={tab === id}
                    className={`macro-news-tab ${tab === id ? 'active' : ''}`}
                    onClick={() => setTab(id)}
                  >
                    {t(`macro.tabs.${id}`)}
                    {id !== 'all' && counts[id] != null && (
                      <span className="macro-news-tab-count">{counts[id]}</span>
                    )}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="btn btn-ghost tap-target macro-news-refresh"
                disabled={refreshing}
                onClick={handleRefresh}
              >
                {refreshing ? '…' : t('macro.refresh')}
              </button>
            </div>

            <p className="macro-news-tab-desc">{t(`macro.tabDesc.${tab}`)}</p>

            {feed && (
              <p className="macro-news-fetched">
                {t('macro.sourcesMeta', {
                  count: feed.sources_count,
                  date: new Date(feed.fetched_at).toLocaleString(dateLocale),
                })}
              </p>
            )}

            {!feed?.items.length ? (
              <p className="empty-state">{t('macro.noNews')}</p>
            ) : (
              <div className="macro-news-grid">
                {feed.items.map((item, index) => (
                  <NewsCard key={item.id} item={item} index={index} t={t} dateLocale={dateLocale} />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <GrowthFunnelStrip source="news" />

      <footer className="macro-news-disclaimer">
        <p>{t('macro.disclaimer')}</p>
      </footer>
    </div>
  )
}
