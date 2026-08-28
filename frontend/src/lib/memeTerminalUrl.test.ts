import { describe, expect, it } from 'vitest'
import {
  dexHomeUrl,
  memeDexScreenerUrl,
  memeLaunchpadUrl,
  memeTerminalUrl,
  normalizeDexLane,
  sanitizeAddress,
} from './memeTerminalUrl'

describe('memeTerminalUrl', () => {
  it('routes Solana mint to Axiom terminal', () => {
    const url = memeTerminalUrl({
      mint: 'DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump',
      symbol: 'BONK',
      chain: 'solana',
    })
    expect(url).toBe(
      'https://axiom.trade/meme/DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump?chain=sol&pulseChains=sol',
    )
  })

  it('routes robinhood mint to Axiom with chain=robinhood', () => {
    const url = memeTerminalUrl({
      mint: '0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF',
      chain: 'robinhood',
    })
    expect(url).toContain('chain=robinhood')
    expect(url).toContain('pulseChains=robinhood')
  })

  it('strips :4meme junk and uses clean DexScreener or four.meme', () => {
    expect(sanitizeAddress('0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF:4meme')).toBe(
      '0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF',
    )
    const broken = memeTerminalUrl({
      mint: '0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF',
      pairAddress: '0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF:4meme',
      chain: 'bsc',
      source: '4meme',
    })
    expect(broken).toContain('axiom.trade/meme/')
    expect(broken).toContain('chain=bnb')
    const bonding = memeTerminalUrl({
      mint: '0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF',
      chain: 'bsc',
      source: '4meme',
    })
    expect(bonding).toBe('https://four.meme/token/0x41097812aa437256aBbc61Dbe4A0fbCD7Ed0fFfF')
  })

  it('dex screener + launchpad helpers', () => {
    expect(memeDexScreenerUrl({ mint: 'm1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1', chain: 'solana' })).toContain(
      'dexscreener.com/solana/',
    )
    expect(memeLaunchpadUrl({ mint: '0x1234567890123456789012345678901234567890', chain: 'bsc', source: '4meme' })).toBe(
      'https://four.meme/token/0x1234567890123456789012345678901234567890',
    )
  })

  it('dexHomeUrl maps venues to whole-DEX pages', () => {
    expect(dexHomeUrl('raydium')).toBe('https://raydium.io/swap/')
    expect(dexHomeUrl('pumpswap')).toBe('https://pump.fun')
    expect(normalizeDexLane('flapsh')).toBe('flap')
  })
})
