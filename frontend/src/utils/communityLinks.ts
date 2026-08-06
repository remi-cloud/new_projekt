import type { InstrumentCommunity } from '../types'

/** Mirrors backend community_links map (majors + Mag7). Tokenized *X-USD inherit underlying. */
const OFFICIAL: Record<string, Omit<InstrumentCommunity, 'x_official'>> = {
  'BTC-USD': { x: 'https://x.com/bitcoin', website: 'https://bitcoin.org' },
  'ETH-USD': {
    x: 'https://x.com/ethereum',
    discord: 'https://discord.gg/ethereum-org',
    website: 'https://ethereum.org',
  },
  'SOL-USD': {
    x: 'https://x.com/solana',
    discord: 'https://discord.gg/solana',
    website: 'https://solana.com',
  },
  'BNB-USD': { x: 'https://x.com/bnbchain', website: 'https://www.bnbchain.org' },
  'XRP-USD': { x: 'https://x.com/Ripple', website: 'https://ripple.com' },
  'ADA-USD': { x: 'https://x.com/Cardano', website: 'https://cardano.org' },
  'DOGE-USD': { x: 'https://x.com/dogecoin', website: 'https://dogecoin.com' },
  'AVAX-USD': { x: 'https://x.com/avax', website: 'https://www.avax.network' },
  'LINK-USD': { x: 'https://x.com/chainlink', website: 'https://chain.link' },
  'DOT-USD': { x: 'https://x.com/Polkadot', website: 'https://polkadot.network' },
  AAPL: { x: 'https://x.com/Apple', website: 'https://www.apple.com' },
  MSFT: { x: 'https://x.com/Microsoft', website: 'https://www.microsoft.com' },
  GOOGL: { x: 'https://x.com/Google', website: 'https://abc.xyz' },
  AMZN: { x: 'https://x.com/amazon', website: 'https://www.amazon.com' },
  NVDA: { x: 'https://x.com/nvidia', website: 'https://www.nvidia.com' },
  META: { x: 'https://x.com/Meta', website: 'https://about.meta.com' },
  TSLA: { x: 'https://x.com/Tesla', website: 'https://www.tesla.com' },
  JPM: { x: 'https://x.com/jpmorgan', website: 'https://www.jpmorganchase.com' },
  V: { x: 'https://x.com/Visa', website: 'https://www.visa.com' },
  XOM: { x: 'https://x.com/exxonmobil', website: 'https://corporate.exxonmobil.com' },
  COIN: { x: 'https://x.com/coinbase', website: 'https://www.coinbase.com' },
  MSTR: { x: 'https://x.com/MicroStrategy', website: 'https://www.microstrategy.com' },
  GME: { x: 'https://x.com/GameStop', website: 'https://www.gamestop.com' },
  HOOD: { x: 'https://x.com/RobinhoodApp', website: 'https://robinhood.com' },
  PLTR: { x: 'https://x.com/PalantirTech', website: 'https://www.palantir.com' },
  AMD: { x: 'https://x.com/AMD', website: 'https://www.amd.com' },
  INTC: { x: 'https://x.com/intel', website: 'https://www.intel.com' },
  NFLX: { x: 'https://x.com/netflix', website: 'https://www.netflix.com' },
  BA: { x: 'https://x.com/Boeing', website: 'https://www.boeing.com' },
  LMT: { x: 'https://x.com/LockheedMartin', website: 'https://www.lockheedmartin.com' },
  RKLB: { x: 'https://x.com/RocketLab', website: 'https://www.rocketlabusa.com' },
  ASTS: { x: 'https://x.com/AST_SpaceMobile', website: 'https://ast-science.com' },
  TSM: { x: 'https://x.com/TSMC_News', website: 'https://www.tsmc.com' },
  BABA: { x: 'https://x.com/AlibabaGroup', website: 'https://www.alibabagroup.com' },
  ASML: { x: 'https://x.com/ASMLcompany', website: 'https://www.asml.com' },
  SAP: { x: 'https://x.com/SAP', website: 'https://www.sap.com' },
  'PKN.WA': { x: 'https://x.com/ORLEN', website: 'https://www.orlen.pl' },
  'PKO.WA': { x: 'https://x.com/PKOBP', website: 'https://www.pkobp.pl' },
  'PZU.WA': { x: 'https://x.com/search?q=PZU&f=live', website: 'https://www.pzu.pl' },
  IBIT: { x: 'https://x.com/bitcoin', website: 'https://www.ishares.com' },
  FBTC: { x: 'https://x.com/bitcoin', website: 'https://www.fidelity.com' },
  ARKB: { x: 'https://x.com/ARKinvest', website: 'https://www.ark-funds.com' },
  BITO: { x: 'https://x.com/ProShares', website: 'https://www.proshares.com' },
  ETHA: { x: 'https://x.com/ethereum', website: 'https://www.ishares.com' },
  ETHE: { x: 'https://x.com/Grayscale', website: 'https://grayscale.com' },
  GBTC: { x: 'https://x.com/Grayscale', website: 'https://grayscale.com' },
  '^GSPC': { x: 'https://x.com/SPDJIndices', website: 'https://www.spglobal.com/spdji' },
  '^IXIC': { x: 'https://x.com/Nasdaq', website: 'https://www.nasdaq.com' },
  '^DJI': { x: 'https://x.com/DowJones', website: 'https://www.dowjones.com' },
}

function searchTicker(symbol: string): string {
  const s = symbol.trim().toUpperCase()
  if (s.endsWith('-USD')) return s.slice(0, -4)
  if (s.endsWith('X-USD') && s.length > 5) return s.slice(0, -5)
  if (s.startsWith('^')) return s.slice(1)
  return s
}

function lookupOfficial(symbol: string): Omit<InstrumentCommunity, 'x_official'> | null {
  const s = symbol.trim().toUpperCase()
  if (OFFICIAL[s]) return OFFICIAL[s]
  if (s.endsWith('X-USD') && s.length > 5) {
    const und = s.slice(0, -5)
    if (OFFICIAL[und]) return OFFICIAL[und]
  }
  return null
}

/** Prefer API community; else official map; else X search. Always returns `x`. */
export function communityOrFallback(
  symbol: string,
  name?: string | null,
  community?: InstrumentCommunity | null,
): InstrumentCommunity {
  if (community?.x) return community
  const mapped = lookupOfficial(symbol)
  if (mapped?.x) {
    return { ...mapped, x_official: true }
  }
  const q = searchTicker(symbol)
  const namePart = (name || '').split('(')[0].trim()
  const query = namePart && namePart.length < 40 ? `${q} OR ${namePart}` : q
  return {
    x: `https://x.com/search?q=${encodeURIComponent(query)}&f=live`,
    x_official: false,
  }
}
