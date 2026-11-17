import { describe, expect, it } from 'vitest'
import { focusMatches, focusedSymbol } from './focusSymbol'

describe('focus symbol', () => {
  it('matches BTC to BTC-USD and keeps the listed symbol', () => {
    expect(focusMatches('BTC', 'BTC-USD')).toBe(true)
    expect(focusMatches('btc-usd', 'BTC-USD')).toBe(true)
    expect(focusMatches('NG', 'NG=F')).toBe(true)
    expect(focusMatches('ETH', 'BTC-USD')).toBe(false)
    expect(focusedSymbol('BTC', ['ETH-USD', 'BTC-USD'])).toBe('BTC-USD')
  })
})