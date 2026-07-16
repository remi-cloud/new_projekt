import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchMacroCalendar } from '../api'
import { ErrorState } from '../components/Loading'
import { NewsShareMenu } from './NewsShareMenu'
import { useLocale } from '../context/LocaleContext'
import { useLiveFeed } from '../hooks/useLiveFeed'
import { MacroCalendarEvent, MacroCalendarMonth, MacroNewsItem } from '../types'

const CATEGORY_DOT: Record<string, string> = {
  fed: 'fed',
  usa: 'usa',
  macro: 'macro',
  global: 'global',
}

function toDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function parseDateKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function buildMonthGrid(year: number, month: number): (Date | null)[][] {
  const first = new Date(year, month - 1, 1)
  const last = new Date(year, month, 0)
  const startPad = (first.getDay() + 6) % 7
  const days: (Date | null)[] = []

  for (let i = 0; i < startPad; i++) days.push(null)
  for (let d = 1; d <= last.getDate(); d++) {
    days.push(new Date(year, month - 1, d))
  }
  while (days.length % 7 !== 0) days.push(null)

  const weeks: (Date | null)[][] = []
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7))
  }
  return weeks
}

function DayDetail({
  dateKey,
  events,
  news,
  onClose,
}: {
  dateKey: string
  events: MacroCalendarEvent[]
  news: MacroNewsItem[]
  onClose: () => void
}) {
  const { t, dateLocale } = useLocale()
  const d = parseDateKey(dateKey)
  const label = d.toLocaleDateString(dateLocale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <div className="macro-cal-day-panel macro-cal-panel-enter">
      <div className="macro-cal-day-panel-head">
        <h3>{label}</h3>
        <button
          type="button"
          className="macro-cal-day-close tap-target"
          onClick={onClose}
          aria-label={t('macro.cal.close')}
        >
          ✕
        </button>
      </div>

      {events.length === 0 && news.length === 0 ? (
        <p className="macro-cal-day-empty">{t('macro.cal.noEvents')}</p>
      ) : (
        <>
          {events.length > 0 && (
            <section className="macro-cal-day-section">
              <h4>{t('macro.cal.eventsTitle')}</h4>
              <ul className="macro-cal-day-events">
                {events.map((ev) => (
                  <li key={ev.id} className="macro-cal-day-event">
                    <div className="macro-cal-day-event-head">
                      <span className={`macro-news-cat macro-news-cat-${ev.category}`}>
                        {t(`macro.category.${ev.category as 'fed' | 'usa' | 'macro' | 'global'}`)}
                      </span>
                      <span className="macro-calendar-region">{ev.region}</span>
                      <span className="macro-cal-event-time">{ev.time_utc} UTC</span>
                    </div>
                    <p className="macro-cal-event-title">{ev.title}</p>
                    {ev.impact === 'high' && <span className="macro-news-impact">{t('macro.highImpact')}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {news.length > 0 && (
            <section className="macro-cal-day-section">
              <h4>{t('macro.cal.newsTitle')}</h4>
              <ul className="macro-cal-day-news">
                {news.map((item) => (
                  <li key={item.id} className="macro-cal-news-item">
                    <div className="macro-cal-news-row">
                      {item.url ? (
                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="macro-cal-news-link">
                          <span className={`macro-news-cat macro-news-cat-${item.category}`}>
                            {t(`macro.category.${item.category}`)}
                          </span>
                          {item.title}
                        </a>
                      ) : (
                        <span className="macro-cal-news-link">{item.title}</span>
                      )}
                      <NewsShareMenu title={item.title} url={item.url} source={item.source} compact />
                    </div>
                    {item.image_url && (
                      <img
                        className="macro-cal-news-thumb"
                        src={item.image_url}
                        alt=""
                        loading="lazy"
                        decoding="async"
                      />
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}

export function MacroCalendarTab() {
  const { t, dateLocale, weekdays, months, locale } = useLocale()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [data, setData] = useState<MacroCalendarMonth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDay, setSelectedDay] = useState<string | null>(toDateKey(now))

  const load = useCallback(async (y: number, m: number, silent = false) => {
    if (!silent) setError(null)
    try {
      const res = await fetchMacroCalendar(y, m, locale)
      setData(res)
    } catch {
      if (!silent) setError(t('macro.errors.fetchCalendar'))
    } finally {
      if (!silent) setLoading(false)
    }
  }, [t, locale])

  useLiveFeed((event) => {
    if (event.type === 'macro_news_tick' || event.type === 'macro_news' || event.type === 'macro_news_image') {
      void load(year, month, true)
    }
  })

  useEffect(() => {
    setLoading(true)
    void load(year, month)
  }, [year, month, load])

  useEffect(() => {
    const pollMs = (data?.poll_interval_seconds ?? 120) * 1000
    const id = window.setInterval(() => void load(year, month, true), pollMs)
    return () => window.clearInterval(id)
  }, [load, year, month, data?.poll_interval_seconds])

  // #region agent log
  useEffect(() => {
    if (!data) return
    const grid = document.querySelector('.macro-cal-grid') as HTMLElement | null
    const wrap = document.querySelector('.macro-cal-grid-wrap') as HTMLElement | null
    const cells = document.querySelectorAll('.macro-cal-cell:not(.macro-cal-cell-empty)')
    const weekdays = document.querySelectorAll('.macro-cal-weekday')
    const dayCard = document.querySelector('.macro-cal-day-card') as HTMLElement | null
    const gStyle = grid ? getComputedStyle(grid) : null
    const c0 = cells[0] as HTMLElement | undefined
    const cStyle = c0 ? getComputedStyle(c0) : null
    const sheets = [...document.styleSheets]
    let cssHasGridRule = false
    let cssRuleCount = 0
    try {
      for (const sheet of sheets) {
        const rules = sheet.cssRules
        if (!rules) continue
        for (const rule of rules) {
          const text = rule.cssText || ''
          if (text.includes('.macro-cal-grid')) {
            cssHasGridRule = true
            cssRuleCount += 1
          }
        }
      }
    } catch {
      /* cross-origin sheets */
    }
    fetch('http://127.0.0.1:7575/ingest/c916b008-4eaa-4854-8387-506d24f3ea58', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'f64a8a' },
      body: JSON.stringify({
        sessionId: 'f64a8a',
        runId: 'pre-fix',
        hypothesisId: 'A,B,C,D,E',
        location: 'MacroCalendarTab.tsx:layoutProbe',
        message: 'macro calendar computed layout probe',
        data: {
          hasGridEl: !!grid,
          hasDayCard: !!dayCard,
          cellCount: cells.length,
          weekdayCount: weekdays.length,
          gridDisplay: gStyle?.display ?? null,
          gridTemplateColumns: gStyle?.gridTemplateColumns ?? null,
          gridWidth: grid?.getBoundingClientRect().width ?? null,
          wrapWidth: wrap?.getBoundingClientRect().width ?? null,
          cellDisplay: cStyle?.display ?? null,
          cellWidth: c0?.getBoundingClientRect().width ?? null,
          cellHeight: c0?.getBoundingClientRect().height ?? null,
          cssHasGridRule,
          cssRuleCount,
          href: window.location.href,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {})
  }, [data, year, month, selectedDay])
  // #endregion

  const eventsByDate = useMemo(() => {
    const map: Record<string, MacroCalendarEvent[]> = {}
    for (const ev of data?.events ?? []) {
      const key = ev.event_date.slice(0, 10)
      if (!map[key]) map[key] = []
      map[key].push(ev)
    }
    return map
  }, [data?.events])

  const newsByDate = useMemo(() => {
    const map: Record<string, MacroNewsItem[]> = {}
    for (const item of data?.news ?? []) {
      const key = item.published_at.slice(0, 10)
      if (!map[key]) map[key] = []
      map[key].push(item)
    }
    return map
  }, [data?.news])

  const weeks = useMemo(() => buildMonthGrid(year, month), [year, month])
  const todayKey = toDateKey(now)

  const goPrev = () => {
    if (month === 1) {
      setYear((y) => y - 1)
      setMonth(12)
    } else {
      setMonth((m) => m - 1)
    }
  }

  const goNext = () => {
    if (month === 12) {
      setYear((y) => y + 1)
      setMonth(1)
    } else {
      setMonth((m) => m + 1)
    }
  }

  const goToday = () => {
    const tday = new Date()
    setYear(tday.getFullYear())
    setMonth(tday.getMonth() + 1)
    setSelectedDay(toDateKey(tday))
  }

  if (loading && !data) {
    return <div className="page-loading macro-page-loading">{t('macro.loadingCalendar')}</div>
  }
  if (error && !data) return <ErrorState message={error} onRetry={() => load(year, month)} />

  const selectedEvents = selectedDay ? eventsByDate[selectedDay] ?? [] : []
  const selectedNews = selectedDay ? newsByDate[selectedDay] ?? [] : []

  return (
    <div className="macro-cal-view macro-cal-enter">
      <div className="macro-cal-toolbar">
        <button
          type="button"
          className="macro-cal-nav tap-target"
          onClick={goPrev}
          aria-label={t('macro.cal.prevMonth')}
        >
          ‹
        </button>
        <h3 className="macro-cal-month-title">
          {months[month - 1]} {year}
        </h3>
        <button
          type="button"
          className="macro-cal-nav tap-target"
          onClick={goNext}
          aria-label={t('macro.cal.nextMonth')}
        >
          ›
        </button>
        <button type="button" className="btn btn-ghost tap-target macro-cal-today" onClick={goToday}>
          {t('macro.cal.today')}
        </button>
      </div>

      {data && (
        <p className="macro-news-fetched">
          {t('macro.cal.monthMeta', { n: data.events.length })}
          {data.news.length > 0 && ` · ${t('macro.cal.newsMeta', { n: data.news.length })}`}
          {' · '}
          {t('macro.cal.refreshMeta', { sec: data.poll_interval_seconds ?? 120 })}
          {' · '}
          {new Date(data.fetched_at).toLocaleString(dateLocale)}
        </p>
      )}

      <div className="macro-cal-layout">
        <div className="macro-cal-grid-wrap">
          <div className="macro-cal-weekdays">
            {weekdays.map((wd) => (
              <span key={wd} className="macro-cal-weekday">
                {wd}
              </span>
            ))}
          </div>

          <div className="macro-cal-grid">
            {weeks.flat().map((day, idx) => {
              if (!day) {
                return <div key={`empty-${idx}`} className="macro-cal-cell macro-cal-cell-empty" />
              }
              const key = toDateKey(day)
              const dayEvents = eventsByDate[key] ?? []
              const dayNews = newsByDate[key] ?? []
              const isToday = key === todayKey
              const isSelected = key === selectedDay
              const cats = [...new Set(dayEvents.map((e) => e.category))]

              return (
                <button
                  key={key}
                  type="button"
                  className={`macro-cal-cell tap-target macro-cal-cell-anim ${isToday ? 'macro-cal-cell-today' : ''} ${isSelected ? 'macro-cal-cell-selected' : ''} ${dayEvents.length ? 'macro-cal-cell-has-events' : ''}`}
                  style={{ animationDelay: `${(idx % 7) * 0.03}s` }}
                  onClick={() => setSelectedDay(key)}
                >
                  <span className="macro-cal-day-num">{day.getDate()}</span>
                  {(dayEvents.length > 0 || dayNews.length > 0) && (
                    <div className="macro-cal-dots">
                      {cats.slice(0, 3).map((cat) => (
                        <span key={cat} className={`macro-cal-dot macro-cal-dot-${CATEGORY_DOT[cat] ?? 'macro'}`} />
                      ))}
                      {dayEvents.length > 3 && <span className="macro-cal-more">+{dayEvents.length - 3}</span>}
                    </div>
                  )}
                  {dayEvents.length > 0 && (
                    <span className="macro-cal-cell-count">{dayEvents.length}</span>
                  )}
                </button>
              )
            })}
          </div>

          <div className="macro-cal-legend">
            <span><i className="macro-cal-dot macro-cal-dot-fed" /> {t('macro.cal.legendFed')}</span>
            <span><i className="macro-cal-dot macro-cal-dot-usa" /> {t('macro.cal.legendUsa')}</span>
            <span><i className="macro-cal-dot macro-cal-dot-macro" /> {t('macro.cal.legendMacro')}</span>
            <span><i className="macro-cal-dot macro-cal-dot-global" /> {t('macro.cal.legendGlobal')}</span>
          </div>
        </div>

        {selectedDay && (
          <DayDetail
            dateKey={selectedDay}
            events={selectedEvents}
            news={selectedNews}
            onClose={() => setSelectedDay(null)}
          />
        )}
      </div>
    </div>
  )
}
