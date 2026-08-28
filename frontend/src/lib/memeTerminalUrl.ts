/**
 * Exchange / terminal deep-links for meme launches.
 * Solana → Axiom terminal; other chains → DexScreener (never mint:4meme junk).
 */

export type MemeTerminalTarget = {
  mint?: string | null
  symbol?: string | null
  chain?: string | null
  pairAddress?: string | null
  url?: string | null
  source?: string | null
  dexId?: string | null
}

function normChain(chain: string | null | undefined): string {
  const c = (chain || '').toLowerCase().trim()
  if (c === 'sol' || c === 'solana') return 'solana'
  if (c === 'bsc' || c === 'bnb' || c === 'binance') return 'bsc'
  if (c === 'eth' || c === 'ethereum') return 'ethereum'
  return c || 'solana'
}

function isSolana(chain: string): boolean {
  return chain === 'solana'
}

/** Axiom session chain codes (force correct chain context in deep links). */
function axiomChainCode(chain: string): string | null {
  const map: Record<string, string> = {
    solana: 'sol',
    bsc: 'bnb',
    ethereum: 'eth',
    robinhood: 'robinhood',
  }
  return map[chain] ?? null
}

/** Chain-aware Axiom meme terminal URL. */
export function axiomMemeUrl(mint: string, chain: string): string {
  const ch = normChain(chain)
  const axiomChain = axiomChainCode(ch) ?? 'sol'
  const base = `https://axiom.trade/meme/${encodeURIComponent(mint)}`
  const q = new URLSearchParams({ chain: axiomChain, pulseChains: axiomChain })
  return `${base}?${q.toString()}`
}

function usesAxiomTerminal(chain: string): boolean {
  return ['solana', 'bsc', 'ethereum', 'robinhood'].includes(chain)
}

/** Strip `:4meme` / `:flap` fake pair suffixes and accidental `bsc:0x…` ids. */
export function sanitizeAddress(value: string | null | undefined): string {
  let raw = (value || '').trim()
  if (!raw) return ''
  raw = raw.replace(/:(4meme|flap|pump|pumpfun|bonding)$/i, '').trim()
  if (raw.includes(':') && !raw.startsWith('0x')) {
    const [head, tail] = raw.split(':')
    if (['bsc', 'solana', 'ethereum', 'base', 'sol', 'eth'].includes(head.toLowerCase()) && tail) {
      return tail.trim()
    }
  }
  return raw
}

function looksLikeAddress(addr: string, chain: string): boolean {
  if (!addr || addr.includes(':')) return false
  if (['bsc', 'ethereum', 'base', 'arbitrum', 'polygon'].includes(chain)) {
    return /^(0x)?[0-9a-fA-F]{40}$/.test(addr)
  }
  if (chain === 'solana') return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(addr)
  return addr.length >= 8
}

/** Primary terminal: Axiom for Solana, DexScreener otherwise. */
export function memeTerminalUrl(t: MemeTerminalTarget): string | null {
  const mint = sanitizeAddress(t.mint)
  const symbol = (t.symbol || '').trim()
  const chain = normChain(t.chain)
  const pair = sanitizeAddress(t.pairAddress)
  const existing = (t.url || '').trim()
  const source = (t.source || t.dexId || '').toLowerCase()

  if ((source.includes('4meme') || source.includes('four')) && mint && !pair) {
    return `https://four.meme/token/${mint}`
  }

  if (usesAxiomTerminal(chain) && mint && looksLikeAddress(mint, chain)) {
    return axiomMemeUrl(mint, chain)
  }

  const path = pair && looksLikeAddress(pair, chain) ? pair : mint
  if (path && looksLikeAddress(path, chain)) {
    // Do not encodeURIComponent the whole path with colons — use raw clean address
    return `https://dexscreener.com/${chain}/${path}`
  }

  const q = mint || symbol
  if (q) {
    if (isSolana(chain)) return `https://axiom.trade/?q=${encodeURIComponent(q)}`
    return `https://dexscreener.com/search?q=${encodeURIComponent(q)}`
  }

  if (existing && /^https?:\/\//i.test(existing) && !/:4meme|%3A4meme/i.test(existing)) {
    return existing
  }
  return null
}

export function memeDexScreenerUrl(t: MemeTerminalTarget): string | null {
  const mint = sanitizeAddress(t.mint)
  const symbol = (t.symbol || '').trim()
  const chain = normChain(t.chain)
  const pair = sanitizeAddress(t.pairAddress)
  const path = pair && looksLikeAddress(pair, chain) ? pair : mint
  if (path && looksLikeAddress(path, chain)) {
    return `https://dexscreener.com/${chain}/${path}`
  }
  if (symbol) return `https://dexscreener.com/search?q=${encodeURIComponent(symbol)}`
  return null
}

export function memeLaunchpadUrl(t: MemeTerminalTarget): string | null {
  const mint = sanitizeAddress(t.mint)
  const chain = normChain(t.chain)
  const source = (t.source || t.dexId || '').toLowerCase()
  const existing = (t.url || '').trim()
  if (existing && /^https?:\/\//i.test(existing) && !existing.includes('dexscreener.com') && !/:4meme/i.test(existing)) {
    return existing
  }
  if (!mint) return null
  if (source.includes('4meme') || source.includes('four')) {
    return `https://four.meme/token/${mint}`
  }
  if (source.includes('pump') && isSolana(chain)) {
    return `https://pump.fun/${mint}`
  }
  if (isSolana(chain) && mint.toLowerCase().endsWith('pump')) {
    return `https://pump.fun/${mint}`
  }
  return null
}

const DEX_ALIASES: Record<string, string> = {
  pumpswap: 'pumpfun',
  'pump.fun': 'pumpfun',
  pump_fun: 'pumpfun',
  pump: 'pumpfun',
  flapsh: 'flap',
  'flap.fun': 'flap',
  pancake: 'pancakeswap',
  pancakeswap_v2: 'pancakeswap',
  pancakeswap_v3: 'pancakeswap',
  four: '4meme',
  fourmeme: '4meme',
}

/** Stable Dex Arena lane key from dex_id / source. */
export function normalizeDexLane(dexId?: string | null, source?: string | null): string {
  let raw = (dexId || source || '').toLowerCase().trim()
  if (!raw) return 'other'
  if (DEX_ALIASES[raw]) return DEX_ALIASES[raw]
  if (raw.includes('pump')) return 'pumpfun'
  if (raw.includes('pancake')) return 'pancakeswap'
  if (raw.includes('flap')) return 'flap'
  if (raw.includes('4meme') || raw.includes('four')) return '4meme'
  if (raw.includes('raydium')) return 'raydium'
  if (raw.includes('orca')) return 'orca'
  if (raw.includes('meteora')) return 'meteora'
  if (['dex', 'gecko', 'geckoterminal', 'profile', 'boost'].includes(raw)) return 'other'
  return raw.replace(/\s+/g, '').slice(0, 32) || 'other'
}

/** Homepage / discovery for a whole DEX (not a token pair). */
export function dexHomeUrl(dexId?: string | null, chain?: string | null): string {
  const lane = normalizeDexLane(dexId)
  const ch = normChain(chain)
  const homes: Record<string, string> = {
    pumpfun: 'https://pump.fun',
    raydium: 'https://raydium.io/swap/',
    pancakeswap: 'https://pancakeswap.finance',
    flap: 'https://dexscreener.com/bsc?dexIds=flapsh',
    '4meme': 'https://four.meme',
    orca: 'https://www.orca.so',
    meteora: 'https://app.meteora.ag',
  }
  if (homes[lane]) return homes[lane]
  if (lane === 'other') return `https://dexscreener.com/${ch}`
  return `https://dexscreener.com/${ch}?dexIds=${encodeURIComponent(lane)}`
}
