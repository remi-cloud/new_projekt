import { useEffect, useState } from 'react'
import { fetchMonthPumpSnippet, type MonthPumpSnippet as Snippet } from '../api'
import { useSeasonalityInfo } from '../context/SeasonalityInfoContext'
import { useLocale } from '../context/LocaleContext'

export function MonthPumpSnippet({ month }: { month: number }) {
  const { t } = useLocale()
  const { openMonth } = useSeasonalityInfo()
  const [data, setData] = useState<Snippet | null>(null)

  useEffect(() => {
    let alive = true
    fetchMonthPumpSnippet(month, 3)
      .then((d) => {
        if (alive) setData(d)
      })
      .catch(() => {
        if (alive) setData(null)
      })
    return () => {
      alive = false
    }
  }, [month])

  if (!data?.text) return null

  return (
    <div className="month-pump-snippet">
      <p className="pres-next-term-note">{data.text}</p>
      <button type="button" className="link-btn tap-target" onClick={() => openMonth(month)}>
        {t('cycles.pumpSeeRanking')}
      </button>
    </div>
  )
}
