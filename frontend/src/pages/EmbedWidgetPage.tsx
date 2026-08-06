import { useCallback, useEffect, useState } from 'react'
import { fetchEmbedCycle, type EmbedCyclePayload } from '../api'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { formatThrownError, resolveApiMessage } from '../i18n/utils'

/** Minimal standalone widget (used in iframe). */
export function EmbedWidgetPage() {
  const { phase, signal } = useDomainLabels()
  const [data, setData] = useState<EmbedCyclePayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await fetchEmbedCycle())
      setError(null)
    } catch (err) {
      setData(null)
      setError(formatThrownError(err, resolveApiMessage('embedFailed')))
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 60000)
    return () => window.clearInterval(id)
  }, [load])

  return (
    <div className="embed-widget-root">
      <div className="cycle-embed-card">
        {data ? (
          <>
            <div className="cycle-embed-brand">{data.brand}</div>
            <div className="cycle-embed-phase">
              {phase(data.phase)} · {signal[data.signal as keyof typeof signal] ?? data.signal}
            </div>
            <div className="cycle-embed-stats">
              <span>Day {data.days_since_ath}</span>
              <span>${Math.round(data.current_price).toLocaleString()}</span>
              <span>{data.progress_pct.toFixed(0)}%</span>
            </div>
            <p>{data.rationale}</p>
            <div className="cycle-embed-foot">
              <a href="/live" target="_blank" rel="noreferrer">
                Live →
              </a>
              <span>{data.disclaimer}</span>
            </div>
          </>
        ) : error ? (
          <p className="embed-widget-error">{error}</p>
        ) : (
          <p>Loading cycle…</p>
        )}
      </div>
    </div>
  )
}
