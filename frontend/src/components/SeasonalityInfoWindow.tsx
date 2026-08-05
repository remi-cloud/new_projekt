import { useEffect, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchInstrumentCalendar,
  fetchMonthPumps,
  type InstrumentCalendarResponse,
  type MonthPumpsResponse,
} from '../api'
import { useSeasonalityInfo } from '../context/SeasonalityInfoContext'
import { useLocale } from '../context/LocaleContext'

function fmt(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return '—'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

const CLASS_FILTERS = ['', 'stock', 'etf', 'commodity', 'bond', 'crypto', 'forex', 'index'] as const

export function SeasonalityInfoWindow() {
  const { t, locale } = useLocale()
  const { target, close, openInstrument, openMonth } = useSeasonalityInfo()
  const titleId = useId()
  const [inst, setInst] = useState<InstrumentCalendarResponse | null>(null)
  const [monthData, setMonthData] = useState<MonthPumpsResponse | null>(null)
  const [classFilter, setClassFilter] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!target) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [target, close])

  useEffect(() => {
    if (!target) {
      setInst(null)
      setMonthData(null)
      setError(null)
      setLoading(false)
      return
    }
    let alive = true
    setLoading(true)
    setError(null)
    if (target.mode === 'instrument') {
      setMonthData(null)
      fetchInstrumentCalendar(target.symbol)
        .then((d) => {
          if (alive) setInst(d)
        })
        .catch((e) => {
          if (alive) setError(e instanceof Error ? e.message : 'error')
        })
        .finally(() => {
          if (alive) setLoading(false)
        })
    } else {
      setInst(null)
      fetchMonthPumps(target.month, {
        class: classFilter || undefined,
        limit: 30,
      })
        .then((d) => {
          if (alive) setMonthData(d)
        })
        .catch((e) => {
          if (alive) setError(e instanceof Error ? e.message : 'error')
        })
        .finally(() => {
          if (alive) setLoading(false)
        })
    }
    return () => {
      alive = false
    }
  }, [target, classFilter])

  if (!target) return null

  const monthLabel = (m: { label_pl: string; label_en: string }) =>
    locale === 'pl' ? m.label_pl : m.label_en

  return (
    <div className="seasonality-modal-backdrop" role="presentation" onClick={close}>
      <div
        className="seasonality-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="seasonality-modal-head">
          <h3 id={titleId}>
            {target.mode === 'instrument'
              ? t('cycles.pumpWindowInstrument')
              : t('cycles.pumpWindowMonth')}
          </h3>
          <button type="button" className="link-btn tap-target" onClick={close}>
            {t('cycles.pumpClose')}
          </button>
        </div>

        {loading && <p className="empty-state">{t('layout.loading')}</p>}
        {error && <p className="empty-state">{error}</p>}

        {target.mode === 'instrument' && inst && (
          <>
            <p className="seasonality-modal-sub">
              <strong>{inst.symbol}</strong> · {inst.name} · {inst.asset_class} · {inst.region}
            </p>
            {inst.narrative && <p className="pres-next-term-note">{inst.narrative}</p>}
            <div className="ob-month-strip seasonality-inst-strip">
              {inst.months.map((m) => {
                const up = (m.avg_return_pct ?? 0) >= 0
                return (
                  <button
                    key={m.month}
                    type="button"
                    className={`ob-month ${m.avg_return_pct == null ? 'empty' : up ? 'up' : 'down'}`}
                    title={`${monthLabel(m)}: ${fmt(m.avg_return_pct)}`}
                    onClick={() => openMonth(m.month)}
                  >
                    <span>{monthLabel(m)}</span>
                    <span>{fmt(m.avg_return_pct)}</span>
                  </button>
                )
              })}
            </div>
            <div className="seasonality-strong-weak">
              <div>
                <span className="ob-side bid">{t('cycles.pumpStrongest')}</span>
                <ul>
                  {inst.strongest_months.map((m) => (
                    <li key={`s-${m.month}`}>
                      {monthLabel(m)} {fmt(m.avg_return_pct)}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <span className="ob-side ask">{t('cycles.pumpWeakest')}</span>
                <ul>
                  {inst.weakest_months.map((m) => (
                    <li key={`w-${m.month}`}>
                      {monthLabel(m)} {fmt(m.avg_return_pct)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <p className="pres-next-term-note">{inst.note}</p>
            <Link className="link-btn" to={`/instrument/${encodeURIComponent(inst.symbol)}`} onClick={close}>
              {t('cycles.pumpOpenInstrument')}
            </Link>
          </>
        )}

        {target.mode === 'month' && monthData && (
          <>
            <p className="seasonality-modal-sub">
              {monthLabel(monthData)} · n={monthData.universe_n}
            </p>
            <div className="cycle-order-book-filters" role="group">
              {CLASS_FILTERS.map((c) => (
                <button
                  key={c || 'all'}
                  type="button"
                  className={`link-btn tap-target ${classFilter === c ? 'active' : ''}`}
                  onClick={() => setClassFilter(c)}
                >
                  {c ? c : t('cycles.pumpFilterAll')}
                </button>
              ))}
            </div>
            <div className="seasonality-pump-cols">
              <div>
                <h4 className="ob-side bid">{t('cycles.pumpPumped')}</h4>
                <ul className="seasonality-pump-list">
                  {monthData.pumped.map((e) => (
                    <li key={`p-${e.symbol}`}>
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => openInstrument(e.symbol)}
                      >
                        {e.symbol}
                      </button>
                      <span className="ob-markets">
                        {e.asset_class} · {fmt(e.avg_return_pct)}
                        {e.win_rate != null ? ` · ${(e.win_rate * 100).toFixed(0)}%` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="ob-side ask">{t('cycles.pumpDrained')}</h4>
                <ul className="seasonality-pump-list">
                  {monthData.drained.map((e) => (
                    <li key={`d-${e.symbol}`}>
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => openInstrument(e.symbol)}
                      >
                        {e.symbol}
                      </button>
                      <span className="ob-markets">
                        {e.asset_class} · {fmt(e.avg_return_pct)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <p className="pres-next-term-note">{monthData.note}</p>
          </>
        )}
      </div>
    </div>
  )
}
