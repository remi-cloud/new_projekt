import { useEffect, useState } from 'react'
import { fetchIntramonth, type IntramonthResponse } from '../api'
import { useLocale } from '../context/LocaleContext'

function fmt(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return '—'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

type Props = {
  month: number
  universe: 'us' | 'btc'
  onClose: () => void
}

export function IntramonthSeasonalityPanel({ month, universe, onClose }: Props) {
  const { t } = useLocale()
  const [data, setData] = useState<IntramonthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    fetchIntramonth(month, universe)
      .then((d) => {
        if (alive) {
          setData(d)
          setError(null)
        }
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : 'error')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [month, universe])

  const monthLabel = t(`cyclesCard.${[
    'monthJan', 'monthFeb', 'monthMar', 'monthApr', 'monthMay', 'monthJun',
    'monthJul', 'monthAug', 'monthSep', 'monthOct', 'monthNov', 'monthDec',
  ][month - 1]}`)

  return (
    <div className="intramonth-panel" role="region" aria-label={t('cyclesCard.intramonthTitle')}>
      <div className="intramonth-head">
        <div>
          <h3 className="intramonth-title">
            {t('cyclesCard.intramonthTitle')} · {monthLabel}
          </h3>
          <p className="intramonth-sub">
            {data?.universe_label ?? (universe === 'us' ? 'USA' : 'BTC')} · {t('cyclesCard.intramonthWeeks')}
          </p>
        </div>
        <button type="button" className="link-btn tap-target" onClick={onClose}>
          {t('cyclesCard.intramonthClose')}
        </button>
      </div>

      {loading && <p className="empty-state">{t('layout.loading')}</p>}
      {error && <p className="empty-state">{error}</p>}

      {data && (
        <>
          <div className="intramonth-weeks">
            {data.weeks.map((w) => {
              const up = w.bias === 'up' || (w.avg_return_pct != null && w.avg_return_pct >= 0)
              return (
                <div
                  key={w.week}
                  className={`intramonth-week ${up ? 'up' : 'down'}`}
                  title={`${w.label} (${w.day_range}): ${fmt(w.avg_return_pct)} n=${w.n}`}
                >
                  <span className="intramonth-week-label">{w.label}</span>
                  <span className="intramonth-week-range">{w.day_range}</span>
                  <span className="intramonth-week-val">{fmt(w.avg_return_pct)}</span>
                </div>
              )
            })}
          </div>

          <div className="intramonth-days" role="list">
            {data.days.map((d) => {
              const up = d.bias === 'up' || (d.avg_return_pct != null && d.avg_return_pct >= 0)
              const empty = d.avg_return_pct == null
              return (
                <div
                  key={d.day}
                  className={`intramonth-day ${empty ? 'empty' : up ? 'up' : 'down'}`}
                  title={`D${d.day} (W${d.week}): ${fmt(d.avg_return_pct)} n=${d.n}`}
                  role="listitem"
                >
                  <span className="intramonth-day-n">{d.day}</span>
                  <span className="intramonth-day-v">{empty ? '·' : fmt(d.avg_return_pct)}</span>
                </div>
              )
            })}
          </div>

          <p className="pres-next-term-note">{data.note}</p>
        </>
      )}
    </div>
  )
}
