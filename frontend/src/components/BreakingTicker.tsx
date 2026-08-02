import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchBroadcast } from '../api'
import { BroadcastResponse } from '../types'

const POLL_MS = 5_000

/** Always-on live results tape; turns red in the 2-min breaking window. */
export default function BreakingTicker() {
  const [data, setData] = useState<BroadcastResponse | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const b = await fetchBroadcast(false)
        if (alive) setData(b)
      } catch {
        /* keep last */
      }
    }
    void load()
    const id = setInterval(load, POLL_MS)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  const text = useMemo(() => {
    if (!data?.lines?.length) return ''
    return data.lines.join('   ✦   ')
  }, [data])

  if (!data?.visible || !text) return null

  const breaking = data.mode === 'breaking'
  const clock = new Date(data.generated_at).toLocaleTimeString('pl-PL')

  return (
    <div
      className={`breaking-ticker${breaking ? ' is-breaking' : ' is-live'}`}
      role="status"
      aria-live="polite"
    >
      <div className="breaking-ticker-label">
        <span className="breaking-live">{breaking ? 'BREAKING' : 'NA ŻYWO'}</span>
        <span className="breaking-timer">
          {data.live_count != null
            ? `${data.live_count}/${data.quote_count ?? '—'} · ${clock}`
            : clock}
          {breaking && data.seconds_remaining > 0 ? ` · ${data.seconds_remaining}s` : ''}
        </span>
      </div>
      <div className="breaking-ticker-track">
        <div className="breaking-ticker-marquee">
          <span>{text}</span>
          <span aria-hidden>{text}</span>
        </div>
      </div>
      {data.setup && (
        <Link to={data.setup.path} className="breaking-ticker-cta">
          {data.setup.side} {data.setup.symbol}
        </Link>
      )}
    </div>
  )
}
