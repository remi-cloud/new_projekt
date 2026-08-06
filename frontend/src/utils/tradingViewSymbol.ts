import { AssetClass, Region } from '../types'

/** Map Yahoo/internal symbols → TradingView exchange:SYMBOL */
export function toTradingViewSymbol(
  symbol: string,
  assetClass?: AssetClass,
  region?: Region,
): string {
  // xStocks: chart the underlying equity (price exposure proxy)
  if (assetClass === 'tokenized' && symbol.endsWith('-USD')) {
    const base = symbol.replace(/-USD$/i, '').toUpperCase()
    const underlying = base.endsWith('X') ? base.slice(0, -1) : base
    const nasdaq = new Set([
      'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
      'AVGO', 'COST', 'NFLX', 'AMD', 'INTC', 'ADBE', 'PYPL', 'QCOM',
      'PLTR', 'COIN', 'HOOD', 'MSTR', 'CRCL', 'GME',
    ])
    if (nasdaq.has(underlying)) return `NASDAQ:${underlying}`
    if (['SPY', 'QQQ', 'VTI', 'GLD', 'IBIT'].includes(underlying)) return `AMEX:${underlying}`
    return `NYSE:${underlying}`
  }

  if (symbol.endsWith('-USD')) {
    const base = symbol.replace('-USD', '')
    return `BINANCE:${base}USDT`
  }

  if (symbol.endsWith('.WA')) return `GPW:${symbol.replace('.WA', '')}`
  if (symbol.endsWith('.KS')) return `KRX:${symbol.replace('.KS', '')}`
  if (symbol.endsWith('.T')) return `TSE:${symbol.replace('.T', '')}`
  if (symbol.endsWith('.PA')) return `EURONEXT:${symbol.replace('.PA', '')}`
  if (symbol.endsWith('.SW')) return `SIX:${symbol.replace('.SW', '')}`
  if (symbol.endsWith('.TA')) return `TASE:${symbol.replace('.TA', '')}`
  if (symbol.endsWith('.SS')) return `SSE:${symbol.replace('.SS', '')}`

  const indexMap: Record<string, string> = {
    '^GSPC': 'SP:SPX',
    '^DJI': 'DJ:DJI',
    '^IXIC': 'NASDAQ:NDX',
    '^NDX': 'NASDAQ:NDX',
    '^RUT': 'RUSSELL:RUT',
    '^VIX': 'CBOE:VIX',
    '^GDAXI': 'XETR:DAX',
    '^FTSE': 'FTSE:UKX',
    '^FCHI': 'EURONEXT:PX1',
    '^STOXX50E': 'EURONEXT:SX5E',
    '^N225': 'TVC:NI225',
    '^HSI': 'HSI:HSI',
    'WIG20.WA': 'GPW:WIG20',
    'WIG.WA': 'GPW:WIG',
  }
  if (indexMap[symbol]) return indexMap[symbol]
  if (symbol.startsWith('^')) return symbol.replace('^', 'TVC:')

  if (assetClass === 'forex' || symbol.includes('=X')) {
    const clean = symbol.replace('=X', '').replace('/', '')
    return `FX_IDC:${clean}`
  }

  if (assetClass === 'bond') return symbol

  const nasdaq = new Set([
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
    'AVGO', 'COST', 'NFLX', 'AMD', 'INTC', 'ADBE', 'PYPL', 'QCOM',
    'RKLB', 'IRDM', 'ASTS', 'GSAT', 'ON', 'ARKX',
  ])
  if (nasdaq.has(symbol)) return `NASDAQ:${symbol}`

  if (region === 'eu' || region === 'pl') {
    if (symbol.includes('.')) return symbol
  }

  if (region === 'asia' && !symbol.includes('.')) {
    if (['TSM', 'BABA'].includes(symbol)) return `NYSE:${symbol}`
    if (symbol === 'SONY') return `NYSE:SONY`
    if (symbol === 'TM') return `NYSE:TM`
  }

  return `NYSE:${symbol}`
}

/** TradingView interval from our preset */
export function presetToTvInterval(preset: string): string {
  const map: Record<string, string> = {
    '1m': '1',
    '5m': '5',
    '15m': '15',
    '30m': '30',
    '1H': '60',
    '4H': '240',
    '1D': 'D',
    '1W': 'W',
    '1M': 'M',
    '3M': 'M',
    '1Y': 'M',
    MAX: 'M',
  }
  return map[preset] ?? 'D'
}
