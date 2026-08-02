import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchBroadcast } from '../api'
import { BroadcastResponse } from '../types'

/** Red TV ticker: 2 minutes every 20 minutes with best setup + econ headlines. */
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
    const id = setInterval(load, 12_000)
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

  return (
    <div className="breaking-ticker" role="status" aria-live="polite">
      <div className="breaking-ticker-label">
        <span className="breaking-live">NA ŻYWO</span>
        <span className="breaking-timer">{data.seconds_remaining}s</span>
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
