export type ChartPreset =
  | '1m'
  | '5m'
  | '15m'
  | '30m'
  | '1H'
  | '4H'
  | '1D'
  | '1W'
  | '1M'
  | '3M'
  | '1Y'
  | 'MAX'

export interface ChartCandle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number | null
}

export interface CycleMarker {
  time: number
  action: 'buy' | 'sell' | 'hold' | 'watch'
  confidence: number
  price: number
  rationale: string
}

export interface ChartResponse {
  symbol: string
  name: string
  interval: string
  range: string
  currency: string
  candles: ChartCandle[]
  current_price: number
  change: number
  change_pct: number
  day_high: number | null
  day_low: number | null
  prev_close: number | null
  cycle_markers?: CycleMarker[]
}

/** Intraday: 1 minute → 4 hours */
export const INTRADAY_CHART_PRESETS: ChartPreset[] = ['1m', '5m', '15m', '30m', '1H', '4H']

export const SWING_CHART_PRESETS: ChartPreset[] = ['1D', '1W', '1M', '3M', '1Y', 'MAX']

export const CHART_PRESETS: ChartPreset[] = [...INTRADAY_CHART_PRESETS, ...SWING_CHART_PRESETS]

/** Short → long: + zooms to shorter range, − to longer. */
export const CHART_ZOOM_LADDER: ChartPreset[] = [
  '1m',
  '5m',
  '15m',
  '30m',
  '1H',
  '4H',
  '1D',
  '1W',
  '1M',
  '3M',
  '1Y',
  'MAX',
]

/** direction -1 = shorter (zoom in), +1 = longer (zoom out). Clamped, no wrap. */
export function stepChartPreset(current: ChartPreset, direction: 1 | -1): ChartPreset {
  const idx = CHART_ZOOM_LADDER.indexOf(current)
  const i = idx < 0 ? CHART_ZOOM_LADDER.indexOf('3M') : idx
  const next = Math.max(0, Math.min(CHART_ZOOM_LADDER.length - 1, i + direction))
  return CHART_ZOOM_LADDER[next]
}

export function canZoomChartIn(current: ChartPreset): boolean {
  return stepChartPreset(current, -1) !== current
}

export function canZoomChartOut(current: ChartPreset): boolean {
  return stepChartPreset(current, 1) !== current
}
