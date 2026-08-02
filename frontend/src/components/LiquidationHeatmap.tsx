import { LiquidationHeatmap as Heatmap } from '../types'

function shade(intensity: number, side: 'long' | 'short'): string {
  const t = Math.max(0.12, Math.min(1, intensity))
  if (side === 'long') {
    // green scale — soft mint → deep emerald
    const g = Math.round(90 + 120 * t)
    const r = Math.round(20 + 40 * (1 - t))
    const b = Math.round(70 + 50 * (1 - t))
    return `rgba(${r}, ${g}, ${b}, ${0.35 + 0.65 * t})`
  }
  // red scale — soft rose → deep crimson
  const r = Math.round(140 + 100 * t)
  const g = Math.round(40 + 30 * (1 - t))
  const b = Math.round(50 + 30 * (1 - t))
  return `rgba(${r}, ${g}, ${b}, ${0.35 + 0.65 * t})`
}

export default function LiquidationHeatmapBar({
  heatmap,
  entry,
  stop,
  tp1,
  tp2,
}: {
  heatmap: Heatmap
  entry?: number
  stop?: number
  tp1?: number
  tp2?: number
}) {
  const { bins, price, range_low, range_high } = heatmap
  const span = range_high - range_low || 1

  const marker = (value: number | undefined, cls: string, label: string) => {
    if (value == null) return null
    const left = ((value - range_low) / span) * 100
    if (left < 0 || left > 100) return null
    return (
      <div className={`hm-marker ${cls}`} style={{ left: `${left}%` }} title={`${label}: ${value}`}>
        <span>{label}</span>
      </div>
    )
  }

  return (
    <div className="heatmap-wrap">
      <div className="heatmap-legend">
        <span className="hm-leg long">Long liq (zieleń)</span>
        <span className="hm-leg mid">Cena</span>
        <span className="hm-leg short">Short liq (czerwień)</span>
      </div>
      <div className="heatmap-track">
        {bins.map((b) => {
          const side = b.dominant === 'long' ? 'long' : 'short'
          const intensity = side === 'long' ? b.long_intensity : b.short_intensity
          return (
            <div
              key={b.price}
              className="heatmap-cell"
              style={{ background: shade(intensity, side) }}
              title={`${b.price.toFixed(2)} · ${side} ${Math.round(intensity * 100)}%`}
            />
          )
        })}
        {marker(price, 'price', 'PX')}
        {marker(entry, 'entry', 'IN')}
        {marker(stop, 'stop', 'SL')}
        {marker(tp1, 'tp', 'TP1')}
        {marker(tp2, 'tp2', 'TP2')}
      </div>
      <div className="heatmap-scale">
        <span>{range_low.toFixed(2)}</span>
        <span>{price.toFixed(2)}</span>
        <span>{range_high.toFixed(2)}</span>
      </div>
    </div>
  )
}
