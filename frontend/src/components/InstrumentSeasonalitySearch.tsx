import { useEffect, useState } from 'react'
import { fetchCalendarSearch, type CalendarSearchHit } from '../api'
import { useSeasonalityInfo } from '../context/SeasonalityInfoContext'
import { useLocale } from '../context/LocaleContext'

export function InstrumentSeasonalitySearch() {
  const { t } = useLocale()
  const { openInstrument, openMonth } = useSeasonalityInfo()
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<CalendarSearchHit[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const term = q.trim()
    if (term.length < 1) {
      setHits([])
      return
    }
    let alive = true
    const timer = window.setTimeout(() => {
      setBusy(true)
      fetchCalendarSearch(term, 12)
        .then((r) => {
          if (alive) setHits(r)
        })
        .catch(() => {
          if (alive) setHits([])
        })
        .finally(() => {
          if (alive) setBusy(false)
        })
    }, 220)
    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [q])

  const nowMonth = new Date().getMonth() + 1

  return (
    <section className="seasonality-search" aria-label={t('cycles.pumpSearchTitle')}>
      <div className="seasonality-search-head">
        <div>
          <h3 className="section-title">{t('cycles.pumpSearchTitle')}</h3>
          <p className="pres-next-term-note">{t('cycles.pumpSearchBody')}</p>
        </div>
        <button
          type="button"
          className="link-btn tap-target"
          onClick={() => openMonth(nowMonth)}
        >
          {t('cycles.pumpThisMonth')}
        </button>
      </div>
      <label className="seasonality-search-label">
        <span className="visually-hidden">{t('cycles.pumpSearchPlaceholder')}</span>
        <input
          type="search"
          className="seasonality-search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('cycles.pumpSearchPlaceholder')}
          autoComplete="off"
        />
      </label>
      {busy && <p className="empty-state">{t('layout.loading')}</p>}
      {hits.length > 0 && (
        <ul className="seasonality-search-hits">
          {hits.map((h) => (
            <li key={h.symbol}>
              <button
                type="button"
                className="seasonality-search-hit tap-target"
                onClick={() => {
                  openInstrument(h.symbol)
                  setQ('')
                  setHits([])
                }}
              >
                <strong>{h.symbol}</strong>
                <span>
                  {h.name} · {h.asset_class} · {h.region}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
