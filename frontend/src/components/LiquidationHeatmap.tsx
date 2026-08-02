import { LiquidationHeatmap as Heatmap } from '../types'

/** CoinGlass-like terminal palette: bright green long / crimson short by intensity. */
function cellColor(longI: number, shortI: number): string {
  const side = longI >= shortI ? 'long' : 'short'
  const t = Math.max(0, Math.min(1, side === 'long' ? longI : shortI))
  if (t < 0.04) return 'rgba(8, 14, 18, 0.92)'
  if (side === 'long') {
    // dark forest → neon mint/yellow-green hotspots
    const r = Math.round(10 + 40 * t + 180 * Math.pow(t, 2.2))
    const g = Math.round(40 + 180 * t)
    const b = Math.round(30 + 40 * (1 - t))
    return `rgba(${r}, ${g}, ${b}, ${0.45 + 0.55 * t})`
  }
  const r = Math.round(80 + 175 * t)
  const g = Math.round(18 + 30 * (1 - t))
  const b = Math.round(40 + 20 * (1 - t))
  return `rgba(${r}, ${g}, ${b}, ${0.45 + 0.55 * t})`
}

function pct(value: number, lo: number, hi: number): number {
  const span = hi - lo || 1
  return ((value - lo) / span) * 100
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
  const { bins, columns, price, range_low, range_high } = heatmap
  const grid = columns && columns.length > 0 ? columns : bins.length ? [bins] : []
  const rows = grid[0]?.length ?? 0
  const cols = grid.length

  // Price high at top → reverse row index when rendering
  const yLabels = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const p = range_high - f * (range_high - range_low)
    return { price: p, top: 100 - pct(p, range_low, range_high) }
  })

  const hLine = (value: number | undefined, cls: string, label: string) => {
    if (value == null || rows === 0) return null
    const top = 100 - pct(value, range_low, range_high)
    if (top < -2 || top > 102) return null
    return (
      <div className={`hm2-hline ${cls}`} style={{ top: `${top}%` }}>
        <span>{label}</span>
      </div>
    )
  }

  return (
    <div className="heatmap-wrap hm2">
      <div className="heatmap-legend">
        <span className="hm-leg long">Long liq ↓</span>
        <span className="hm-leg mid">czas →</span>
        <span className="hm-leg short">Short liq ↑</span>
      </div>

      <div className="hm2-frame">
        <div className="hm2-yaxis" aria-hidden>
          {yLabels.map((m) => (
            <span key={m.price} style={{ top: `${m.top}%` }}>
              {m.price.toFixed(2)}
            </span>
          ))}
        </div>

        <div className="hm2-canvas">
          <div
            className="hm2-grid"
            style={{
              gridTemplateColumns: `repeat(${cols}, 1fr)`,
              gridTemplateRows: `repeat(${rows}, 1fr)`,
            }}
          >
            {/* Fill column-major visually: for each row from high→low, each col left→right */}
            {Array.from({ length: rows }, (_, ri) => {
              const priceIdx = rows - 1 - ri
              return grid.map((col, ci) => {
                const cell = col[priceIdx]
                if (!cell) return null
                return (
                  <div
                    key={`${ci}-${priceIdx}`}
                    className="hm2-cell"
                    style={{
                      gridColumn: ci + 1,
                      gridRow: ri + 1,
                      background: cellColor(cell.long_intensity, cell.short_intensity),
                    }}
                    title={`${cell.price.toFixed(2)} · L ${Math.round(cell.long_intensity * 100)}% / S ${Math.round(cell.short_intensity * 100)}%`}
                  />
                )
              })
            })}
          </div>

          {hLine(price, 'price', 'PX')}
          {hLine(entry, 'entry', 'IN')}
          {hLine(stop, 'stop', 'SL')}
          {hLine(tp1, 'tp', 'TP1')}
          {hLine(tp2, 'tp2', 'TP2')}

          <div className="hm2-now" title="Teraz" />
        </div>

        <div className="hm2-intensity" aria-hidden>
          <div className="hm2-intensity-bar" />
          <span>słabo</span>
          <span>silnie</span>
        </div>
      </div>

      <div className="heatmap-scale hm2-scale">
        <span>wcześniej</span>
        <span>
          {range_low.toFixed(2)} — {range_high.toFixed(2)}
        </span>
        <span>teraz</span>
      </div>
    </div>
  )
}
