import { useEffect, useMemo, useRef, useState } from 'react'
import { HeatmapBin, LiqPrediction, LiquidationHeatmap as Heatmap } from '../types'

type Vec3 = { x: number; y: number; z: number }
type Face = { a: Vec3; b: Vec3; c: Vec3; d: Vec3; color: [number, number, number]; depth: number }

function intensityOf(cell: HeatmapBin): number {
  return Math.max(cell.long_intensity, cell.short_intensity, 0)
}

function rgbFor(cell: HeatmapBin): [number, number, number] {
  const longI = cell.long_intensity
  const shortI = cell.short_intensity
  const side = longI >= shortI ? 'long' : 'short'
  // Boost mid intensities so opposite sides read as clearly green vs red
  const raw = side === 'long' ? longI : shortI
  const t = Math.max(0, Math.min(1, Math.pow(raw, 0.72)))
  // Dim near-zero cells so markers/path stay readable
  if (t < 0.04) return [14, 18, 22]
  if (side === 'long') {
    const r = Math.round(10 + 28 * t)
    const g = Math.round(90 + 150 * t)
    const b = Math.round(70 + 50 * t)
    return [r, Math.min(255, g), Math.min(255, b)]
  }
  const r = Math.round(140 + 110 * t)
  const g = Math.round(24 + 20 * (1 - t))
  const b = Math.round(36 + 16 * (1 - t))
  return [Math.min(255, r), g, b]
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

function sampleHeight(
  grid: HeatmapBin[][],
  t: number,
  price: number,
  rangeLow: number,
  rangeHigh: number,
  heightScale: number,
): number {
  const cols = grid.length
  const rows = grid[0]?.length ?? 0
  if (!cols || !rows) return 0
  const ci = Math.max(0, Math.min(cols - 1, Math.round(t * (cols - 1))))
  const span = rangeHigh - rangeLow || 1
  const ri = Math.max(0, Math.min(rows - 1, Math.round(((price - rangeLow) / span) * (rows - 1))))
  return intensityOf(grid[ci][ri]) * heightScale
}

function priceToZ(price: number, rangeLow: number, rangeHigh: number): number {
  const span = rangeHigh - rangeLow || 1
  const n = (price - rangeLow) / span // 0..1 low→high
  return -((n) * 2 - 1) // match mesh z mapping
}

function drawLabelPill(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  color: string,
  opts?: { fontSize?: number; padX?: number; padY?: number },
) {
  const fontSize = opts?.fontSize ?? 12
  const padX = opts?.padX ?? 7
  const padY = opts?.padY ?? 4
  ctx.save()
  ctx.font = `700 ${fontSize}px IBM Plex Mono, monospace`
  const tw = ctx.measureText(text).width
  const bx = x
  const by = y - fontSize - padY
  const bw = tw + padX * 2
  const bh = fontSize + padY * 2
  ctx.fillStyle = 'rgba(4, 10, 12, 0.88)'
  ctx.strokeStyle = color
  ctx.lineWidth = 1.4
  ctx.beginPath()
  const r = 5
  ctx.moveTo(bx + r, by)
  ctx.arcTo(bx + bw, by, bx + bw, by + bh, r)
  ctx.arcTo(bx + bw, by + bh, bx, by + bh, r)
  ctx.arcTo(bx, by + bh, bx, by, r)
  ctx.arcTo(bx, by, bx + bw, by, r)
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  ctx.fillStyle = color
  ctx.fillText(text, bx + padX, by + bh - padY - 1)
  ctx.restore()
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
  opts?: { dashed?: boolean; alpha?: number; withLabel?: boolean },
) {
  const cols = grid.length
  const rows = grid[0]?.length ?? 0
  if (!cols || !rows) return
  const span = rangeHigh - rangeLow || 1
  const ri = Math.round(((price - rangeLow) / span) * (rows - 1))
  if (ri < 0 || ri >= rows) return

  const dashed = opts?.dashed ?? true
  const alpha = opts?.alpha ?? 0.9
  const withLabel = opts?.withLabel ?? true

  ctx.save()
  ctx.globalAlpha = alpha
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = 2.2
  if (dashed) ctx.setLineDash([7, 5])
  ctx.beginPath()
  // Sample fewer points — cleaner line, less visual noise
  const step = Math.max(1, Math.floor(cols / 28))
  for (let ci = 0; ci < cols; ci += step) {
    const cell = grid[ci][ri]
    const nx = (ci / (cols - 1)) * 2 - 1
    const ny = (ri / (rows - 1)) * 2 - 1
    const nz = intensityOf(cell) * heightScale
    const p = project({ x: nx, y: nz + 0.03, z: -ny }, w, h, yaw, pitch, zoom)
    if (ci === 0) ctx.moveTo(p.x, p.y)
    else ctx.lineTo(p.x, p.y)
  }
  // ensure last point
  {
    const ci = cols - 1
    const cell = grid[ci][ri]
    const nx = 1
    const ny = (ri / (rows - 1)) * 2 - 1
    const nz = intensityOf(cell) * heightScale
    const p = project({ x: nx, y: nz + 0.03, z: -ny }, w, h, yaw, pitch, zoom)
    ctx.lineTo(p.x, p.y)
  }
  ctx.stroke()
  ctx.setLineDash([])
  if (withLabel) {
    const end = project(
      {
        x: 1,
        y: intensityOf(grid[cols - 1][ri]) * heightScale + 0.06,
        z: -((ri / (rows - 1)) * 2 - 1),
      },
      w,
      h,
      yaw,
      pitch,
      zoom,
    )
    drawLabelPill(ctx, label, end.x + 4, end.y - 2, color)
  }
  ctx.restore()
}

/** Glowing AI path: position levels → liquidation magnet. */
function drawPredictionPath(
  ctx: CanvasRenderingContext2D,
  grid: HeatmapBin[][],
  prediction: LiqPrediction,
  rangeLow: number,
  rangeHigh: number,
  w: number,
  h: number,
  yaw: number,
  pitch: number,
  zoom: number,
  heightScale: number,
) {
  const path = prediction.path
  if (!path.length) return

  const pts = path.map((pt) => {
    const x = pt.t * 2 - 1
    const z = priceToZ(pt.price, rangeLow, rangeHigh)
    const y =
      sampleHeight(grid, pt.t, pt.price, rangeLow, rangeHigh, heightScale) + 0.06 + pt.intensity * 0.08
    return project({ x, y, z }, w, h, yaw, pitch, zoom)
  })

  ctx.save()
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'

  // Soft underlay (less bloom — clearer on dark terrain)
  ctx.strokeStyle = prediction.direction === 'down' ? 'rgba(248,113,113,0.22)' : 'rgba(52,211,153,0.22)'
  ctx.lineWidth = 8
  ctx.beginPath()
  pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)))
  ctx.stroke()

  const grad = ctx.createLinearGradient(pts[0].x, pts[0].y, pts[pts.length - 1].x, pts[pts.length - 1].y)
  if (prediction.direction === 'down') {
    grad.addColorStop(0, '#fca5a5')
    grad.addColorStop(0.55, '#f87171')
    grad.addColorStop(1, '#fde047')
  } else {
    grad.addColorStop(0, '#6ee7b7')
    grad.addColorStop(0.55, '#34d399')
    grad.addColorStop(1, '#fde047')
  }
  ctx.strokeStyle = grad
  ctx.lineWidth = 3.2
  ctx.shadowColor = 'rgba(0,0,0,0.45)'
  ctx.shadowBlur = 6
  ctx.beginPath()
  pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)))
  ctx.stroke()
  ctx.shadowBlur = 0

  // Only unique roles — avoid stacking TP1+TP2+IN stems on top of each other
  const seenRoles = new Set<string>()
  const anchors = prediction.anchors.filter((a) => {
    if (seenRoles.has(a.role)) return false
    seenRoles.add(a.role)
    return true
  })

  for (const a of anchors) {
    const nearest = path.reduce(
      (best, pt, idx) => {
        const d = Math.abs(pt.t - a.t) + Math.abs(pt.price - a.price) / Math.max(a.price, 1)
        return d < best.d ? { d, idx } : best
      },
      { d: Infinity, idx: 0 },
    )
    const target = pts[nearest.idx]
    const ax = a.t * 2 - 1
    const az = priceToZ(a.price, rangeLow, rangeHigh)
    const ay =
      sampleHeight(grid, a.t, a.price, rangeLow, rangeHigh, heightScale) + 0.16
    const ap = project({ x: ax, y: ay, z: az }, w, h, yaw, pitch, zoom)

    const color =
      a.role === 'stop'
        ? '#f87171'
        : a.role === 'liq'
          ? '#fde047'
          : a.role === 'entry'
            ? '#fbbf24'
            : '#34d399'

    // Short stem only — no long dashed clutter across the map
    ctx.strokeStyle = color
    ctx.globalAlpha = 0.75
    ctx.lineWidth = 1.8
    ctx.setLineDash(a.role === 'stop' ? [3, 3] : [])
    ctx.beginPath()
    ctx.moveTo(ap.x, ap.y)
    ctx.lineTo(target.x, target.y)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.globalAlpha = 1
    ctx.fillStyle = color
    ctx.strokeStyle = 'rgba(4,10,12,0.9)'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.arc(ap.x, ap.y, a.role === 'liq' ? 6 : 4.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.stroke()
    drawLabelPill(ctx, a.label, ap.x + 8, ap.y - 4, color, { fontSize: 11 })
  }

  const last = pts[pts.length - 1]
  const prev = pts[Math.max(0, pts.length - 3)]
  const ang = Math.atan2(last.y - prev.y, last.x - prev.x)
  ctx.fillStyle = '#fde047'
  ctx.strokeStyle = 'rgba(4,10,12,0.85)'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.moveTo(last.x, last.y)
  ctx.lineTo(last.x - 11 * Math.cos(ang - 0.4), last.y - 11 * Math.sin(ang - 0.4))
  ctx.lineTo(last.x - 11 * Math.cos(ang + 0.4), last.y - 11 * Math.sin(ang + 0.4))
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  drawLabelPill(ctx, 'LIQ', last.x + 8, last.y - 2, '#fde047', { fontSize: 12 })
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
    prediction?: LiqPrediction | null
    showLevelLines?: boolean
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

  // Flatter terrain — markers stay readable above the mesh
  const heightScale = 0.38
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

  // Axis labels with contrast pills
  drawLabelPill(ctx, 'czas →', cssW * 0.72, cssH * 0.93, 'rgba(226,232,240,0.95)', {
    fontSize: 11,
  })
  drawLabelPill(ctx, 'cena ↑', cssW * 0.05, cssH * 0.2, 'rgba(226,232,240,0.95)', {
    fontSize: 11,
  })
  drawLabelPill(ctx, 'wysokość = siła liq', cssW * 0.05, cssH * 0.09, 'rgba(148,163,184,0.95)', {
    fontSize: 10,
  })

  const hasPath = Boolean(meta.prediction?.path?.length)
  const showLines = meta.showLevelLines !== false

  // When AI path is on: only PX + SL lines (anchors cover IN/TP/LIQ) — less spaghetti
  if (showLines) {
    drawMarkerLine(
      ctx,
      grid,
      meta.price,
      meta.rangeLow,
      meta.rangeHigh,
      '#f8fafc',
      'PX',
      cssW,
      cssH,
      yaw,
      pitch,
      zoom,
      heightScale,
      { dashed: false, alpha: 0.75, withLabel: !hasPath },
    )
    if (meta.stop != null) {
      drawMarkerLine(
        ctx,
        grid,
        meta.stop,
        meta.rangeLow,
        meta.rangeHigh,
        '#f87171',
        'SL',
        cssW,
        cssH,
        yaw,
        pitch,
        zoom,
        heightScale,
        { dashed: true, alpha: hasPath ? 0.45 : 0.85, withLabel: !hasPath },
      )
    }
    if (!hasPath) {
      if (meta.entry != null) {
        drawMarkerLine(
          ctx,
          grid,
          meta.entry,
          meta.rangeLow,
          meta.rangeHigh,
          '#fbbf24',
          'IN',
          cssW,
          cssH,
          yaw,
          pitch,
          zoom,
          heightScale,
        )
      }
      if (meta.tp1 != null) {
        drawMarkerLine(
          ctx,
          grid,
          meta.tp1,
          meta.rangeLow,
          meta.rangeHigh,
          '#34d399',
          'TP1',
          cssW,
          cssH,
          yaw,
          pitch,
          zoom,
          heightScale,
        )
      }
      if (meta.tp2 != null) {
        drawMarkerLine(
          ctx,
          grid,
          meta.tp2,
          meta.rangeLow,
          meta.rangeHigh,
          '#2dd4bf',
          'TP2',
          cssW,
          cssH,
          yaw,
          pitch,
          zoom,
          heightScale,
          { alpha: 0.7 },
        )
      }
    }
  }

  if (hasPath && meta.prediction) {
    drawPredictionPath(
      ctx,
      grid,
      meta.prediction,
      meta.rangeLow,
      meta.rangeHigh,
      cssW,
      cssH,
      yaw,
      pitch,
      zoom,
      heightScale,
    )
  }
}

export default function LiquidationHeatmapBar({
  heatmap,
  entry,
  stop,
  tp1,
  tp2,
  prediction,
}: {
  heatmap: Heatmap
  entry?: number
  stop?: number
  tp1?: number
  tp2?: number
  prediction?: LiqPrediction | null
}) {
  const { bins, columns, price, range_low, range_high } = heatmap
  const grid = useMemo(
    () => (columns && columns.length > 0 ? columns : bins.length ? [bins] : []),
    [columns, bins],
  )
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  // Slightly more top-down — easier to read levels vs peaks
  const [yaw, setYaw] = useState(-0.32)
  const [pitch, setPitch] = useState(0.42)
  const [zoom, setZoom] = useState(1.08)
  const [showLevelLines, setShowLevelLines] = useState(true)
  const [showPathMeta, setShowPathMeta] = useState(true)
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
          prediction,
          showLevelLines,
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
  }, [
    grid,
    price,
    range_low,
    range_high,
    entry,
    stop,
    tp1,
    tp2,
    prediction,
    yaw,
    pitch,
    zoom,
    showLevelLines,
  ])

  const dirArrow =
    prediction?.direction === 'up' ? '↑' : prediction?.direction === 'down' ? '↓' : '↔'

  const fmt = (n?: number) => (n == null || Number.isNaN(n) ? '—' : n.toFixed(2))

  const levelKey = [
    { id: 'px', label: 'PX', value: price, tone: 'px' },
    { id: 'in', label: 'IN', value: entry, tone: 'in' },
    { id: 'sl', label: 'SL', value: stop, tone: 'sl' },
    { id: 'tp1', label: 'TP1', value: tp1, tone: 'tp' },
    { id: 'tp2', label: 'TP2', value: tp2, tone: 'tp2' },
    {
      id: 'liq',
      label: 'LIQ',
      value: prediction?.target_price,
      tone: 'liq',
    },
  ].filter((x) => x.value != null)

  return (
    <div className="heatmap-wrap hm3">
      <div className="heatmap-legend">
        <span className="hm-leg long">LONG · zieleń</span>
        <span className="hm-leg mid">wyższe = silniejsza liq · ścieżka IN → LIQ</span>
        <span className="hm-leg short">SHORT · czerwień</span>
      </div>

      <ul className="hm-level-key" aria-label="Poziomy na mapie">
        {levelKey.map((row) => (
          <li key={row.id} className={`hm-key-chip tone-${row.tone}`}>
            <strong>{row.label}</strong>
            <span>{fmt(row.value)}</span>
          </li>
        ))}
      </ul>

      <div className="hm3-toolbar">
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setYaw((y) => y - 0.15)}>
          ⟲
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setYaw((y) => y + 0.15)}>
          ⟳
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPitch((p) => Math.min(1.05, p + 0.06))}>
          Góra
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setPitch((p) => Math.max(0.12, p - 0.06))}>
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
            setYaw(-0.32)
            setPitch(0.42)
            setZoom(1.08)
          }}
        >
          Reset
        </button>
        <button
          type="button"
          className={`btn btn-ghost btn-sm${showLevelLines ? ' active-tool' : ''}`}
          onClick={() => setShowLevelLines((v) => !v)}
          title="Linie poziomów na mapie"
        >
          Linie
        </button>
        {prediction && (
          <button
            type="button"
            className={`btn btn-ghost btn-sm${showPathMeta ? ' active-tool' : ''}`}
            onClick={() => setShowPathMeta((v) => !v)}
          >
            Opis AI
          </button>
        )}
      </div>

      {prediction && showPathMeta && (
        <div className={`tool-inline-meta dir-${prediction.direction}`}>
          <strong>
            {dirArrow} {prediction.summary}
          </strong>
          <span>
            pull↑ {prediction.pull_up.toFixed(1)} · pull↓ {prediction.pull_down.toFixed(1)} · mom{' '}
            {prediction.momentum.toFixed(2)} · {prediction.confidence.toFixed(0)}%
          </span>
        </div>
      )}

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
          setPitch(Math.max(0.12, Math.min(1.05, drag.current.pitch + dy * 0.004)))
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
          zakres {range_low.toFixed(2)} — {range_high.toFixed(2)}
        </span>
        <span>teraz</span>
      </div>
    </div>
  )
}
