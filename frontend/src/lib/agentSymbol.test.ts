import { describe, expect, it } from 'vitest'
import { resolveAgentSymbol } from './agentSymbol'

const known = ['LQD', 'BTC-USD', 'SPCX', 'SPACEX', 'AAPL']

describe('resolveAgentSymbol', () => {
  it('maps LIQ typo to LQD', () => {
    const r = resolveAgentSymbol('LIQ', known)
    expect(r).toEqual({ ok: true, symbol: 'LQD', aliasedFrom: 'LIQ' })
  })

  it('maps SpaceX aliases to SPCX', () => {
    expect(resolveAgentSymbol('SPACEX', known)).toEqual({
      ok: true,
      symbol: 'SPCX',
      aliasedFrom: 'SPACEX',
    })
    expect(resolveAgentSymbol('spacex', known)).toEqual({
      ok: true,
      symbol: 'SPCX',
      aliasedFrom: 'SPACEX',
    })
  })

  it('accepts known symbols', () => {
    expect(resolveAgentSymbol('lqd', known)).toEqual({ ok: true, symbol: 'LQD' })
    expect(resolveAgentSymbol('btc', known)).toEqual({
      ok: true,
      symbol: 'BTC-USD',
      aliasedFrom: 'BTC',
    })
  })

  it('blocks unknown when catalog loaded', () => {
    expect(resolveAgentSymbol('ZZZZ', known)).toEqual({
      ok: false,
      reason: 'unknown',
      input: 'ZZZZ',
    })
  })
})
