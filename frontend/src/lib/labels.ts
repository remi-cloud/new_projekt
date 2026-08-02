import { AssetClass, SignalAction } from '../types'

export const ASSET_LABELS: Record<AssetClass, string> = {
  crypto: 'Krypto',
  stock: 'Akcje',
  index: 'Indeksy',
  bond: 'Obligacje',
  commodity: 'Surowce',
  forex: 'Forex',
}

export const SIGNAL_LABELS: Record<SignalAction, string> = {
  buy: 'Kupuj',
  sell: 'Sprzedaj',
  hold: 'Trzymaj',
  watch: 'Obserwuj',
}

export const PHASE_LABELS: Record<string, string> = {
  bear: 'Spadkowa',
  accumulation: 'Akumulacja',
  bull: 'Wzrostowa',
  distribution: 'Dystrybucja',
  neutral: 'Neutralna',
  year_1: 'Faza 1',
  year_2: 'Faza 2',
  year_3: 'Faza 3',
  year_4: 'Faza 4',
}

export const MODEL_LABELS: Record<string, string> = {
  alpha: 'Model Alpha',
  beta: 'Model Beta',
  bitcoin_cycle: 'Model Alpha',
  presidential_cycle: 'Model Beta',
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
  return SIGNAL_LABELS[action as SignalAction] ?? action
}
