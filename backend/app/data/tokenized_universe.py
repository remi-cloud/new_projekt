"""Tokenized US stocks & ETFs (xStocks / Backed) — Yahoo Finance *-USD tickers.

Educational catalog only. xStocks are geo-restricted (not US/UK/AU/CA in many venues).
Symbols verified against Yahoo chart API (SYMBOLX-USD).
"""

from __future__ import annotations

# Yahoo uses uppercase ticker like AAPLX-USD (tokenized Apple).
TOKENIZED_UNIVERSE: list[dict] = [
    # ── Mag7 / mega-cap xStocks ──
    {"symbol": "AAPLX-USD", "name": "Apple xStock", "asset_class": "tokenized", "region": "us", "underlying": "AAPL"},
    {"symbol": "MSFTX-USD", "name": "Microsoft xStock", "asset_class": "tokenized", "region": "us", "underlying": "MSFT"},
    {"symbol": "GOOGLX-USD", "name": "Alphabet xStock", "asset_class": "tokenized", "region": "us", "underlying": "GOOGL"},
    {"symbol": "AMZNX-USD", "name": "Amazon xStock", "asset_class": "tokenized", "region": "us", "underlying": "AMZN"},
    {"symbol": "NVDAX-USD", "name": "NVIDIA xStock", "asset_class": "tokenized", "region": "us", "underlying": "NVDA"},
    {"symbol": "METAX-USD", "name": "Meta xStock", "asset_class": "tokenized", "region": "us", "underlying": "META"},
    {"symbol": "TSLAX-USD", "name": "Tesla xStock", "asset_class": "tokenized", "region": "us", "underlying": "TSLA"},
    # ── Tech / growth ──
    {"symbol": "AVGOX-USD", "name": "Broadcom xStock", "asset_class": "tokenized", "region": "us", "underlying": "AVGO"},
    {"symbol": "ORCLX-USD", "name": "Oracle xStock", "asset_class": "tokenized", "region": "us", "underlying": "ORCL"},
    {"symbol": "PLTRX-USD", "name": "Palantir xStock", "asset_class": "tokenized", "region": "us", "underlying": "PLTR"},
    {"symbol": "INTCX-USD", "name": "Intel xStock", "asset_class": "tokenized", "region": "us", "underlying": "INTC"},
    {"symbol": "AMDX-USD", "name": "AMD xStock", "asset_class": "tokenized", "region": "us", "underlying": "AMD"},
    {"symbol": "NFLXX-USD", "name": "Netflix xStock", "asset_class": "tokenized", "region": "us", "underlying": "NFLX"},
    {"symbol": "CRCLX-USD", "name": "Circle xStock", "asset_class": "tokenized", "region": "us", "underlying": "CRCL"},
    {"symbol": "HOODX-USD", "name": "Robinhood xStock", "asset_class": "tokenized", "region": "us", "underlying": "HOOD"},
    {"symbol": "MSTRX-USD", "name": "MicroStrategy xStock", "asset_class": "tokenized", "region": "us", "underlying": "MSTR"},
    {"symbol": "GMEX-USD", "name": "GameStop xStock", "asset_class": "tokenized", "region": "us", "underlying": "GME"},
    {"symbol": "COINX-USD", "name": "Coinbase xStock", "asset_class": "tokenized", "region": "us", "underlying": "COIN"},
    # ── Finance / energy / consumer ──
    {"symbol": "JPMX-USD", "name": "JPMorgan xStock", "asset_class": "tokenized", "region": "us", "underlying": "JPM"},
    {"symbol": "BACX-USD", "name": "Bank of America xStock", "asset_class": "tokenized", "region": "us", "underlying": "BAC"},
    {"symbol": "XOMX-USD", "name": "Exxon xStock", "asset_class": "tokenized", "region": "us", "underlying": "XOM"},
    {"symbol": "CVXX-USD", "name": "Chevron xStock", "asset_class": "tokenized", "region": "us", "underlying": "CVX"},
    {"symbol": "KOX-USD", "name": "Coca-Cola xStock", "asset_class": "tokenized", "region": "us", "underlying": "KO"},
    {"symbol": "PEPX-USD", "name": "Pepsi xStock", "asset_class": "tokenized", "region": "us", "underlying": "PEP"},
    {"symbol": "WMTX-USD", "name": "Walmart xStock", "asset_class": "tokenized", "region": "us", "underlying": "WMT"},
    # ── Tokenized ETFs ──
    {"symbol": "SPYX-USD", "name": "SPDR S&P 500 xStock", "asset_class": "tokenized", "region": "us", "underlying": "SPY"},
    {"symbol": "QQQX-USD", "name": "Invesco QQQ xStock", "asset_class": "tokenized", "region": "us", "underlying": "QQQ"},
    {"symbol": "VTIX-USD", "name": "Vanguard Total Market xStock", "asset_class": "tokenized", "region": "us", "underlying": "VTI"},
    {"symbol": "GLDX-USD", "name": "SPDR Gold Shares xStock", "asset_class": "tokenized", "region": "us", "underlying": "GLD"},
]

# Spot crypto ETFs (traditional wrappers — asset_class etf)
CRYPTO_ETF_UNIVERSE: list[dict] = [
    {"symbol": "IBIT", "name": "iShares Bitcoin Trust", "asset_class": "etf", "region": "us"},
    {"symbol": "FBTC", "name": "Fidelity Wise Origin Bitcoin", "asset_class": "etf", "region": "us"},
    {"symbol": "ARKB", "name": "ARK 21Shares Bitcoin ETF", "asset_class": "etf", "region": "us"},
    {"symbol": "BITO", "name": "ProShares Bitcoin Strategy ETF", "asset_class": "etf", "region": "us"},
    {"symbol": "ETHA", "name": "iShares Ethereum Trust", "asset_class": "etf", "region": "us"},
    {"symbol": "ETHE", "name": "Grayscale Ethereum Trust", "asset_class": "etf", "region": "us"},
    {"symbol": "GBTC", "name": "Grayscale Bitcoin Trust", "asset_class": "etf", "region": "us"},
]
