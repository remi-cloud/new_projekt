import { AssetClass } from '../types'

export function formatPln(amount: number): string {
  return `${amount.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} PLN`
}

export function formatPrice(price: number, assetClass: AssetClass): string {
  if (assetClass === 'forex') return price.toFixed(4)
  if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (price >= 1) return price.toFixed(2)
  return price.toFixed(4)
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('pl-PL')
}
