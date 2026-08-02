import { useEffect, useMemo, useRef, useState } from 'react'
import { HeatmapBin, LiquidationHeatmap as Heatmap } from '../types'

type Vec3 = { x: number; y: number; z: number }
type Face = { a: Vec3; b: Vec3; c: Vec3; d: Vec3; color: [number, number, number]; depth: number }

function intensityOf(cell: HeatmapBin): number {
  return Math.max(cell.long_intensity, cell.short_intensity, 0)
}

function rgbFor(cell: HeatmapBin): [number, number, number] {
  const longI = cell.long_intensity
  const shortI = cell.short_intensity
  const side = longI >= shortI ? 'long' : 'short'
  const t = Math.max(0, Math.min(1, side === 'long' ? longI : shortI))
  if (t < 0.03) return [10, 16, 18]
  if (side === 'long') {
    // deep teal → neon mint → hot yellow-green (sharp peaks)
    const r = Math.round(8 + 30 * t + 210 * t * t)
    const g = Math.round(50 + 190 * t)
    const b = Math.round(40 + 35 * (1 - t))
    return [r, g, b]
  }
  const r = Math.round(90 + 165 * t)
  const g = Math.round(16 + 28 * (1 - t))
  const b = Math.round(36 + 18 * (1 - t))
  return [r, g, b]
}

/** Bilinear upsample for 8K-sharp mesh density without heavier API payload. */
function upsample(grid: HeatmapBin[][], sx: number, sy: number): HeatmapBin[][] {
  const cols = grid.length
  const rows = grid[0]?.length ?? 0
  if (!cols || !rows) return grid
  const outCols = Math.max(cols, Math.round(cols * sx))
  const outRows = Math.max(rows, Math.round(rows * sy))
  const out: HeatmapBin[][] = []
  for (let ci = 0; ci < outCols; ci++) {
    const u = (ci / Math.max(1, outCols - 1)) * (cols - 1)
    const c0 = Math.floor(u)
    const c1 = Math.min(cols - 1, c0 + 1)
    const fu = u - c0
    const col: HeatmapBin[] = []
    for (let ri = 0; ri < outRows; ri++) {
      const v = (ri / Math.max(1, outRows - 1)) * (rows - 1)
      const r0 = Math.floor(v)
      const r1 = Math.min(rows - 1, r0 + 1)
      const fv = v - r0
      const samples = [
        grid[c0][r0],
        grid[c1][r0],
        grid[c0][r1],
        grid[c1][r1],
      ]
      const w00 = (1 - fu) * (1 - fv)
      const w10 = fu * (1 - fv)
      const w01 = (1 - fu) * fv
      const w11 = fu * fv
      const longI =
        samples[0].long_intensity * w00 +
        samples[1].long_intensity * w10 +
        samples[2].long_intensity * w01 +
        samples[3].long_intensity * w11
      const shortI =
        samples[0].short_intensity * w00 +
        samples[1].short_intensity * w10 +
        samples[2].short_intensity * w01 +
        samples[3].short_intensity * w11
      const price =
        samples[0].price * w00 +
        samples[1].price * w10 +
        samples[2].price * w01 +
        samples[3].price * w11
      col.push({
        price,
        long_intensity: longI,
        short_intensity: shortI,
        dominant: longI >= shortI ? 'long' : 'short',
        intensity: Math.max(longI, shortI),
      })
    }
    out.push(col)
  }
  return out
}

function project(
  p: Vec3,
  w: number,
  h: number,
  yaw: number,
  pitch: number,
  zoom: number,
): { x: number; y: number; z: number } {
  const cy = Math.cos(yaw)
  const sy = Math.sin(yaw)
  const cp = Math.cos(pitch)
  const sp = Math.sin(pitch)
  // yaw around Y, then pitch around X
  const x1 = p.x * cy + p.z * sy
  const z1 = -p.x * sy + p.z * cy
  const y2 = p.y * cp - z1 * sp
  const z2 = p.y * sp + z1 * cp
  const persp = 2.6 / (2.6 + z2)
  const scale = Math.min(w, h) * 0.42 * zoom * persp
  return {
    x: w * 0.5 + x1 * scale,
    y: h * 0.58 - y2 * scale,
    z: z2,
  }
}

function shadeRgb(
  rgb: [number, number, number],
  normalY: number,
  depth: number,
): string {
  // Lighting for głębia: brighter tops, darker far faces
  const light = 0.55 + 0.45 * Math.max(0, normalY) - depth * 0.08
  const k = Math.max(0.35, Math.min(1.25, light))
  const r = Math.min(255, Math.round(rgb[0] * k))
  const g = Math.min(255, Math.round(rgb[1] * k))
  const b = Math.min(255, Math.round(rgb[2] * k))
  return `rgb(${r},${g},${b})`
}

function drawMarkerLine(
  ctx: CanvasRenderingContext2D,
  grid: HeatmapBin[][],
  price: number,
  rangeLow: number,
  rangeHigh: number,
  color: string,
  label: string,
  w: number,
  h: number,
  yaw: number,
  pitch: number,
  zoom: number,
  heightScale: number,
) {
  const cols = grid.length
  const rows = grid[0]?.length ?? 0
  if (!cols || !rows) return
  const span = rangeHigh - rangeLow || 1
  const ri = Math.round(((price - rangeLow) / span) * (rows - 1))
  if (ri < 0 || ri >= rows) return

  ctx.save()
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = 1.5
  ctx.setLineDash([5, 4])
  ctx.beginPath()
  for (let ci = 0; ci < cols; ci++) {
    const cell = grid[ci][ri]
    const nx = (ci / (cols - 1)) * 2 - 1
    const ny = (ri / (rows - 1)) * 2 - 1
    const nz = intensityOf(cell) * heightScale
    const p = project({ x: nx, y: nz + 0.02, z: -ny }, w, h, yaw, pitch, zoom)
    if (ci === 0) ctx.moveTo(p.x, p.y)
    else ctx.lineTo(p.x, p.y)
  }
  ctx.stroke()
  ctx.setLineDash([])
  const end = project(
    {
      x: 1,
      y: intensityOf(grid[cols - 1][ri]) * heightScale + 0.04,
      z: -((ri / (rows - 1)) * 2 - 1),
    },
    w,
    h,
    yaw,
    pitch,
    zoom,
  )
  ctx.font = '600 11px IBM Plex Mono, monospace'
  ctx.fillText(label, end.x + 6, end.y - 4)
  ctx.restore()
}

function renderScene(
  canvas: HTMLCanvasElement,
  gridIn: HeatmapBin[][],
  meta: {
    price: number
    rangeLow: number
    rangeHigh: number
    entry?: number
    stop?: number
    tp1?: number
    tp2?: number
  },
  yaw: number,
  pitch: number,
  zoom: number,
) {
  const cssW = canvas.clientWidth || 900
  const cssH = canvas.clientHeight || 420
  // HiDPI / "8K sharpness": push backing store hard on retina
  const dpr = Math.min(window.devicePixelRatio || 1, 3) * 1.5
  const w = Math.round(cssW * dpr)
  const h = Math.round(cssH * dpr)
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w
    canvas.height = h
  }
  const ctx = canvas.getContext('2d', { alpha: false, desynchronized: true })
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'

  // Atmosphere
  const bg = ctx.createLinearGradient(0, 0, 0, cssH)
  bg.addColorStop(0, '#071014')
  bg.addColorStop(0.55, '#0a1418')
  bg.addColorStop(1, '#05090c')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, cssW, cssH)

  // subtle depth fog grid
  ctx.strokeStyle = 'rgba(45, 212, 191, 0.04)'
  ctx.lineWidth = 1
  for (let i = 0; i < 12; i++) {
    const y = (cssH / 12) * i
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(cssW, y)
    ctx.stroke()
  }

  const grid = upsample(gridIn, 2.2, 2.0)
  const cols = grid.length
  const rows = grid[0]?.length ?? 0
  if (!cols || !rows) return

  const heightScale = 0.95
  const faces: Face[] = []

  for (let ci = 0; ci < cols - 1; ci++) {
    for (let ri = 0; ri < rows - 1; ri++) {
      const c00 = grid[ci][ri]
      const c10 = grid[ci + 1][ri]
      const c01 = grid[ci][ri + 1]
      const c11 = grid[ci + 1][ri + 1]
      const x0 = (ci / (cols - 1)) * 2 - 1
      const x1 = ((ci + 1) / (cols - 1)) * 2 - 1
      const z0 = -((ri / (rows - 1)) * 2 - 1)
      const z1 = -(((ri + 1) / (rows - 1)) * 2 - 1)
      const y00 = intensityOf(c00) * heightScale
      const y10 = intensityOf(c10) * heightScale
      const y01 = intensityOf(c01) * heightScale
      const y11 = intensityOf(c11) * heightScale
      const avg = (y00 + y10 + y01 + y11) / 4
      const rgb = rgbFor(c00)
      faces.push({
        a: { x: x0, y: y00, z: z0 },
        b: { x: x1, y: y10, z: z0 },
        c: { x: x1, y: y11, z: z1 },
        d: { x: x0, y: y01, z: z1 },
        color: rgb,
        depth: avg,
      })
    }
  }

  // Painter's algorithm — far faces first for głębia
  faces.sort((f1, f2) => {
    const zA =
      (project(f1.a, cssW, cssH, yaw, pitch, zoom).z +
        project(f1.c, cssW, cssH, yaw, pitch, zoom).z) /
      2
    const zB =
      (project(f2.a, cssW, cssH, yaw, pitch, zoom).z +
        project(f2.c, cssW, cssH, yaw, pitch, zoom).z) /
      2
    return zB - zA
  })

  // Base plane (depth floor)
  const floor: Vec3[] = [
    { x: -1.05, y: 0, z: -1.05 },
    { x: 1.05, y: 0, z: -1.05 },
    { x: 1.05, y: 0, z: 1.05 },
    { x: -1.05, y: 0, z: 1.05 },
  ]
  const fp = floor.map((p) => project(p, cssW, cssH, yaw, pitch, zoom))
  ctx.beginPath()
  ctx.moveTo(fp[0].x, fp[0].y)
  fp.slice(1).forEach((p) => ctx.lineTo(p.x, p.y))
  ctx.closePath()
  ctx.fillStyle = 'rgba(8, 18, 22, 0.92)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(45, 212, 191, 0.18)'
  ctx.stroke()

  for (const face of faces) {
    const pa = project(face.a, cssW, cssH, yaw, pitch, zoom)
    const pb = project(face.b, cssW, cssH, yaw, pitch, zoom)
    const pc = project(face.c, cssW, cssH, yaw, pitch, zoom)
    const pd = project(face.d, cssW, cssH, yaw, pitch, zoom)
    // approximate normal from height slope
    const normalY = 0.35 + face.depth * 0.65
    const depthFog = (pa.z + pc.z) * 0.12
    ctx.beginPath()
    ctx.moveTo(pa.x, pa.y)
    ctx.lineTo(pb.x, pb.y)
    ctx.lineTo(pc.x, pc.y)
    ctx.lineTo(pd.x, pd.y)
    ctx.closePath()
    ctx.fillStyle = shadeRgb(face.color, normalY, depthFog)
    ctx.fill()
    // hairline for ostrość krawędzi
    ctx.strokeStyle = `rgba(0,0,0,${0.12 + face.depth * 0.15})`
    ctx.lineWidth = 0.4
    ctx.stroke()
  }

  // Axis labels
  ctx.fillStyle = 'rgba(168, 181, 174, 0.85)'
  ctx.font = '500 11px Outfit, system-ui, sans-serif'
  ctx.fillText('czas →', cssW * 0.72, cssH * 0.92)
  ctx.fillText('cena ↑', cssW * 0.06, cssH * 0.22)
  ctx.fillText('głębia = natężenie liq', cssW * 0.06, cssH * 0.08)

  drawMarkerLine(
    ctx, grid, meta.price, meta.rangeLow, meta.rangeHigh, '#ffffff', 'PX',
    cssW, cssH, yaw, pitch, zoom, heightScale,
  )
  if (meta.entry != null) {
    drawMarkerLine(
      ctx, grid, meta.entry, meta.rangeLow, meta.rangeHigh, '#e8a317', 'IN',
      cssW, cssH, yaw, pitch, zoom, heightScale,
    )
  }
  if (meta.stop != null) {
    drawMarkerLine(
      ctx, grid, meta.stop, meta.rangeLow, meta.rangeHigh, '#f87171', 'SL',
      cssW, cssH, yaw, pitch, zoom, heightScale,
    )
  }
  if (meta.tp1 != null) {
    drawMarkerLine(
      ctx, grid, meta.tp1, meta.rangeLow, meta.rangeHigh, '#34d399', 'TP1',
      cssW, cssH, yaw, pitch, zoom, heightScale,
    )
  }
  if (meta.tp2 != null) {
    drawMarkerLine(
      ctx, grid, meta.tp2, meta.rangeLow, meta.rangeHigh, '#2dd4bf', 'TP2',
      cssW, cssH, yaw, pitch, zoom, heightScale,
    )
  }
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
  const grid = useMemo(
    () => (columns && columns.length > 0 ? columns : bins.length ? [bins] : []),
    [columns, bins],
  )
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const [yaw, setYaw] = useState(-0.55)
  const [pitch, setPitch] = useState(0.55)
  const [zoom, setZoom] = useState(1.05)
  const drag = useRef<{ x: number; y: number; yaw: number; pitch: number } | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap || !grid.length) return

    const paint = () =>
      renderScene(
        canvas,
        grid,
        {
          price,
          rangeLow: range_low,
          rangeHigh: range_high,
          entry,
          stop,
          tp1,
          tp2,
        },
        yaw,
        pitch,
        zoom,
      )

    paint()
    const ro = new ResizeObserver(() => paint())
    ro.observe(wrap)

    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      setZoom((z) => Math.max(0.7, Math.min(1.7, z - e.deltaY * 0.001)))
    }
    wrap.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      ro.disconnect()
      wrap.removeEventListener('wheel', onWheel)
    }
  }, [grid, price, range_low, range_high, entry, stop, tp1, tp2, yaw, pitch, zoom])

  return (
    <div className="heatmap-wrap hm3">
      <div className="heatmap-legend">
        <span className="hm-leg long">Long liq (zieleń) ↓</span>
        <span className="hm-leg mid">3D · głębia = natężenie · przeciągnij aby obrócić</span>
        <span className="hm-leg short">Short liq (czerwień) ↑</span>
      </div>

      <div className="hm3-toolbar">
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setYaw((y) => y - 0.15)}>
          ⟲
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setYaw((y) => y + 0.15)}>
          ⟳
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPitch((p) => Math.min(1.2, p + 0.08))}>
          Góra
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPitch((p) => Math.max(0.2, p - 0.08))}>
          Dół
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setZoom((z) => Math.min(1.6, z + 0.1))}>
          +
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setZoom((z) => Math.max(0.7, z - 0.1))}>
          −
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => {
            setYaw(-0.55)
            setPitch(0.55)
            setZoom(1.05)
          }}
        >
          Reset
        </button>
      </div>

      <div
        className="hm3-stage"
        ref={wrapRef}
        onPointerDown={(e) => {
          ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
          drag.current = { x: e.clientX, y: e.clientY, yaw, pitch }
        }}
        onPointerMove={(e) => {
          if (!drag.current) return
          const dx = e.clientX - drag.current.x
          const dy = e.clientY - drag.current.y
          setYaw(drag.current.yaw + dx * 0.006)
          setPitch(Math.max(0.15, Math.min(1.25, drag.current.pitch + dy * 0.004)))
        }}
        onPointerUp={() => {
          drag.current = null
        }}
        onPointerLeave={() => {
          drag.current = null
        }}
      >
        <canvas ref={canvasRef} className="hm3-canvas" />
      </div>

      <div className="heatmap-scale hm2-scale">
        <span>wcześniej</span>
        <span>
          {range_low.toFixed(2)} — {range_high.toFixed(2)} · HiDPI 3D
        </span>
        <span>teraz</span>
      </div>
    </div>
  )
}
