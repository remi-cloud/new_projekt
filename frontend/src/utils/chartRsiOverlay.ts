import type { RsiPoint } from './chartIndicators'
import type { UTCTimestamp } from 'lightweight-charts'

const GREEN = { r: 34, g: 197, b: 94 }
const RED = { r: 239, g: 68, b: 68 }

function yForRsi(rsi: number, plotH: number): number {
  const margin = plotH * 0.04
  const band = plotH - margin * 2
  return margin + band * (1 - rsi / 100)
}

function rgba(c: { r: number; g: number; b: number }, a: number): string {
  return `rgba(${c.r},${c.g},${c.b},${a})`
}

function rsiColor(rsi: number): { r: number; g: number; b: number } {
  if (rsi <= 30) return GREEN
  if (rsi >= 70) return RED
  const t = (rsi - 30) / 40
  return {
    r: Math.round(GREEN.r + (RED.r - GREEN.r) * t),
    g: Math.round(GREEN.g + (RED.g - GREEN.g) * t),
    b: Math.round(GREEN.b + (RED.b - GREEN.b) * t),
  }
}

export function drawRsiSmear(
  ctx: CanvasRenderingContext2D,
  plotW: number,
  plotH: number,
  points: RsiPoint[],
  timeToX: (time: UTCTimestamp) => number | null,
) {
  ctx.clearRect(0, 0, plotW, plotH)
  if (points.length < 2 || plotW < 10 || plotH < 10) return

  const y0 = yForRsi(0, plotH)
  const y30 = yForRsi(30, plotH)
  const y70 = yForRsi(70, plotH)
  const y100 = yForRsi(100, plotH)

  // Strefy tła: wyprzedanie / wykupienie
  const coldGrad = ctx.createLinearGradient(0, y30, 0, y0)
  coldGrad.addColorStop(0, 'rgba(34,197,94,0.06)')
  coldGrad.addColorStop(1, 'rgba(34,197,94,0.22)')
  ctx.fillStyle = coldGrad
  ctx.fillRect(0, y30, plotW, y0 - y30)

  const hotGrad = ctx.createLinearGradient(0, y100, 0, y70)
  hotGrad.addColorStop(0, 'rgba(239,68,68,0.22)')
  hotGrad.addColorStop(1, 'rgba(239,68,68,0.06)')
  ctx.fillStyle = hotGrad
  ctx.fillRect(0, y100, plotW, y70 - y100)

  const coords: { x: number; y: number; rsi: number }[] = []
  for (const p of points) {
    const x = timeToX(p.time)
    if (x === null || x < -20 || x > plotW + 20) continue
    coords.push({ x, y: yForRsi(p.value, plotH), rsi: p.value })
  }
  if (coords.length < 2) return

  // Smuga — wypełnienie od dołu do linii RSI
  for (let i = 0; i < coords.length - 1; i++) {
    const a = coords[i]
    const b = coords[i + 1]
    const avgRsi = (a.rsi + b.rsi) / 2
    const col = rsiColor(avgRsi)
    const alpha = avgRsi <= 30 ? 0.42 : avgRsi >= 70 ? 0.48 : 0.22

    ctx.beginPath()
    ctx.moveTo(a.x, y0)
    ctx.lineTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.lineTo(b.x, y0)
    ctx.closePath()
    ctx.fillStyle = rgba(col, alpha)
    ctx.fill()
  }

  // Iluminacja — jaśniejsza linia smugi
  for (let i = 0; i < coords.length - 1; i++) {
    const a = coords[i]
    const b = coords[i + 1]
    const avg = (a.rsi + b.rsi) / 2
    const col = rsiColor(avg)
    const alpha = avg <= 30 ? 0.78 : avg >= 70 ? 0.85 : 0.38

    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.strokeStyle = rgba(col, alpha * 0.35)
    ctx.lineWidth = 7
    ctx.lineCap = 'round'
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.strokeStyle = rgba(col, alpha)
    ctx.lineWidth = 2.5
    ctx.stroke()
  }
}
