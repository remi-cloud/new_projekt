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
