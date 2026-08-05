import { useEffect, useState } from 'react'
import {
  fetchGlobalCycleBook,
  type GlobalBookEntry,
  type GlobalCycleBookResponse,
} from '../api'
import { useSeasonalityInfo } from '../context/SeasonalityInfoContext'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from '../i18n'

function fmt(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return '—'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

function statusClass(status: string): string {
  if (status === 'adopted') return 'adopted'
  if (status === 'watch') return 'watch'
  return 'rejected'
}

const FILTER_KEYS = {
  adopted: 'cycles.bookFilterAdopted',
  watch: 'cycles.bookFilterWatch',
  all: 'cycles.bookFilterAll',
} as const satisfies Record<string, TranslationPath>

const HORIZON_KEYS = {
  monthly: 'cycles.bookHorizonMonthly',
  weekly: 'cycles.bookHorizonWeekly',
  yearly: 'cycles.bookHorizonYearly',
} as const satisfies Record<string, TranslationPath>

const STATUS_KEYS = {
  adopted: 'cycles.bookStatusAdopted',
  watch: 'cycles.bookStatusWatch',
  rejected: 'cycles.bookStatusRejected',
} as const satisfies Record<string, TranslationPath>

export function CycleOrderBook() {
  const { t } = useLocale()
  const { openMonth } = useSeasonalityInfo()
  const [data, setData] = useState<GlobalCycleBookResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'adopted' | 'watch'>('adopted')

  useEffect(() => {
    let alive = true
    fetchGlobalCycleBook(filter === 'all' ? 'all' : filter)
      .then((d) => {
        if (alive) {
          setData(d)
          setError(null)
        }
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : 'error')
      })
    return () => {
      alive = false
    }
  }, [filter])

  const book: GlobalBookEntry[] = data?.order_book ?? []
  const profiles = data?.profiles ?? {}
  const universeIds = Object.keys(profiles)

  return (
    <section className="cycle-order-book" aria-label={t('cycles.bookTitle')}>
      <div className="cycle-order-book-head">
        <div>
          <h3 className="section-title">{t('cycles.bookTitle')}</h3>
          <p className="pres-next-term-note">{t('cycles.bookBody')}</p>
        </div>
        <div className="cycle-order-book-filters" role="group">
          {(['adopted', 'watch', 'all'] as const).map((f) => (
            <button
              key={f}
              type="button"
              className={`link-btn tap-target ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {t(FILTER_KEYS[f])}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="empty-state">{error}</p>}
      {!error && !data && <p className="empty-state">{t('layout.loading')}</p>}

      {data && book.length === 0 && (
        <p className="empty-state">{t('cycles.bookEmpty')}</p>
      )}

      {book.length > 0 && (
        <div className="cycle-order-book-table-wrap">
          <table className="cycle-order-book-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{t('cycles.bookColSlot')}</th>
                <th>{t('cycles.bookColHorizon')}</th>
                <th>{t('cycles.bookColSide')}</th>
                <th>{t('cycles.bookColReturn')}</th>
                <th>{t('cycles.bookColMarkets')}</th>
                <th>{t('cycles.bookColScore')}</th>
                <th>{t('cycles.bookColStatus')}</th>
              </tr>
            </thead>
            <tbody>
              {book.map((e) => (
                <tr key={e.id} className={`ob-row ${statusClass(e.status)} ${e.side}`}>
                  <td>{e.rank}</td>
                  <td>{e.slot_label}</td>
                  <td>{t(HORIZON_KEYS[e.horizon])}</td>
                  <td className={`ob-side ${e.side}`}>
                    {e.side === 'bid' ? t('cycles.bookSideBid') : t('cycles.bookSideAsk')}
                  </td>
                  <td>{fmt(e.avg_return_pct)}</td>
                  <td title={e.markets.join(', ')}>
                    {e.markets_n}/{e.markets_total}{' '}
                    <span className="ob-markets">{e.markets.join(' · ')}</span>
                  </td>
                  <td>{(e.reproduction_score * 100).toFixed(0)}%</td>
                  <td>
                    <span className={`ob-status ${statusClass(e.status)}`}>
                      {t(STATUS_KEYS[e.status])}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {universeIds.length > 0 && (
        <>
          <h4 className="section-title">{t('cycles.bookProfilesTitle')}</h4>
          <div className="cycle-order-book-profiles">
            {universeIds.map((uid) => {
              const p = profiles[uid]
              return (
                <div key={uid} className="ob-profile">
                  <div className="ob-profile-head">
                    <strong>{p.label}</strong>
                    <span className="ob-profile-meta">
                      n={p.symbols_included}/{p.symbols_total}
                    </span>
                  </div>
                  <div className="ob-month-strip" aria-label={p.label}>
                    {p.months.map((m) => {
                      const up = (m.avg_return_pct ?? 0) >= 0
                      return (
                        <button
                          type="button"
                          key={m.month}
                          className={`ob-month clickable ${m.avg_return_pct == null ? 'empty' : up ? 'up' : 'down'}`}
                          title={`${m.label}: ${fmt(m.avg_return_pct)} — ${t('cycles.pumpSeeRanking')}`}
                          onClick={() => openMonth(m.month)}
                        >
                          <span>{m.label}</span>
                          <span>{fmt(m.avg_return_pct)}</span>
                        </button>
                      )
                    })}
                  </div>
                  <div className="ob-week-strip">
                    {p.weeks.map((w) => {
                      const up = (w.avg_return_pct ?? 0) >= 0
                      return (
                        <div
                          key={w.week}
                          className={`ob-week ${up ? 'up' : 'down'}`}
                          title={`${w.label} ${w.day_range}: ${fmt(w.avg_return_pct)}`}
                        >
                          {w.label} {fmt(w.avg_return_pct)}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {data?.meta?.mean_month_corr != null && (
        <p className="pres-next-term-note">
          {t('cycles.bookCorr', {
            month: String(data.meta.mean_month_corr),
            week: String(data.meta.mean_week_corr ?? '—'),
          })}
        </p>
      )}
    </section>
  )
}
