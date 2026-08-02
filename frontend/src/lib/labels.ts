import { AssetClass, SignalAction } from '../types'

export type SignalDirection = 'long' | 'short' | 'neutral'

export const ASSET_LABELS: Record<AssetClass, string> = {
  crypto: 'Krypto',
  stock: 'Akcje',
  index: 'Indeksy',
  bond: 'Obligacje',
  commodity: 'Surowce',
  forex: 'Forex',
}

/** Public labels — only LONG / SHORT / NEUTRAL. */
export const DIRECTION_LABELS: Record<SignalDirection, string> = {
  long: 'LONG',
  short: 'SHORT',
  neutral: 'NEUTRAL',
}

/** Map API action (buy/sell/hold/watch) → direction. */
export function signalDirection(action: string): SignalDirection {
  const a = action.toLowerCase()
  if (a === 'sell' || a === 'short') return 'short'
  if (a === 'hold' || a === 'neutral') return 'neutral'
  if (a === 'buy' || a === 'watch' || a === 'long') return 'long'
  return 'neutral'
}

/** API actions that belong to a direction (for filters / alerts). */
export function actionsForDirection(dir: SignalDirection): SignalAction[] {
  if (dir === 'long') return ['buy', 'watch']
  if (dir === 'short') return ['sell']
  return ['hold']
}

export const SIGNAL_LABELS: Record<SignalAction, string> = {
  buy: 'LONG',
  sell: 'SHORT',
  hold: 'NEUTRAL',
  watch: 'LONG',
}

export const PHASE_LABELS: Record<string, string> = {
  bear: 'Spadkowa',
  accumulation: 'Akumulacja',
  bull: 'Wzrostowa',
  distribution: 'Dystrybucja',
  neutral: 'Neutralna',
  phase_1: 'Faza 1',
  phase_2: 'Faza 2',
  phase_3: 'Faza 3',
  phase_4: 'Faza 4',
}

export const MODEL_LABELS: Record<string, string> = {
  alpha: 'Model Alpha',
  beta: 'Model Beta',
}

export function formatModel(source: string): string {
  return MODEL_LABELS[source] ?? 'Model'
}

export function formatPrice(price: number, assetClass: AssetClass): string {
  if (assetClass === 'forex') return price.toFixed(4)
  if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (price >= 1) return price.toFixed(2)
  return price.toFixed(4)
}

export function formatSignal(action: string): string {
  return DIRECTION_LABELS[signalDirection(action)]
}

export function formatDirection(side: string): string {
  return DIRECTION_LABELS[signalDirection(side)]
}
