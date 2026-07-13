export type ChartPreset = '1D' | '1W' | '1M' | '3M' | '1Y' | 'MAX'

export interface ChartCandle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number | null
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
}
