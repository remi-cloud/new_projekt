import type { AssetClass, SignalAction } from '../types'

export type SignalDirection = 'long' | 'short' | 'neutral'

export const ASSET_LABELS: Record<string, string> = {
  crypto: 'Krypto',
  stock: 'Akcje',
  etf: 'ETF',
  tokenized: 'Tokenizowane',
  index: 'Indeksy',
  bond: 'Obligacje',
  commodity: 'Surowce',
  forex: 'Forex',
}

export const DIRECTION_LABELS: Record<SignalDirection, string> = {
  long: 'LONG',
  short: 'SHORT',
  neutral: 'NEUTRAL',
}

export function signalDirection(action: string): SignalDirection {
  const a = action.toLowerCase()
  if (a === 'sell' || a === 'short') return 'short'
  if (a === 'buy' || a === 'long') return 'long'
  if (a === 'hold' || a === 'watch' || a === 'neutral' || a === 'czekaj') return 'neutral'
  return 'neutral'
}

export const SIGNAL_LABELS: Record<string, string> = {
  buy: 'LONG',
  sell: 'SHORT',
  hold: 'NEUTRAL',
  watch: 'CZEKAJ',
}

export const MODEL_LABELS: Record<string, string> = {
  bitcoin: 'Cykl Bitcoin',
  presidential: 'Cykl prezydencki',
  alpha: 'Cykl Bitcoin',
  beta: 'Cykl prezydencki',
}

export function formatModel(source: string): string {
  return MODEL_LABELS[source] ?? source
}

export function formatPrice(price: number, assetClass?: AssetClass | string): string {
  if (assetClass === 'forex') return price.toFixed(4)
  if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (price >= 1) return price.toFixed(2)
  return price.toFixed(4)
}

export function formatSignal(action: string): string {
  const a = action.toLowerCase()
  if (a in SIGNAL_LABELS) return SIGNAL_LABELS[a]
  return DIRECTION_LABELS[signalDirection(action)]
}

export function formatDirection(side: string): string {
  return DIRECTION_LABELS[signalDirection(side)]
}

export function actionsForDirection(dir: SignalDirection): SignalAction[] {
  if (dir === 'long') return ['buy']
  if (dir === 'short') return ['sell']
  return ['hold', 'watch']
}
