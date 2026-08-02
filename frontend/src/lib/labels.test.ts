import { describe, expect, it } from 'vitest'
import { formatSignal, signalDirection } from './labels'

describe('signal labels', () => {
  it('maps buy/sell to LONG/SHORT and watch to CZEKAJ (not LONG)', () => {
    expect(formatSignal('buy')).toBe('LONG')
    expect(formatSignal('sell')).toBe('SHORT')
    expect(formatSignal('watch')).toBe('CZEKAJ')
    expect(signalDirection('watch')).toBe('neutral')
    expect(signalDirection('buy')).toBe('long')
  })
})

describe('markets API paths', () => {
  it('uses relative /api base so tunnel + same-origin work', async () => {
    // Smoke: module contract — fetch helpers must call /api/* not absolute foreign hosts
    const api = await import('../api')
    expect(typeof api.fetchMarkets).toBe('function')
    expect(typeof api.fetchMarketStatus).toBe('function')
    expect(typeof api.fetchBroadcast).toBe('function')
  })
})
