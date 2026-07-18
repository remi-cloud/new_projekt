"""Default instrument catalog and helpers for the watchlist."""

from __future__ import annotations

DEFAULT_ASSETS: list[dict] = [
    # Crypto
    {"symbol": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto", "source": "yahoo"},
    {"symbol": "ETH-USD", "name": "Ethereum", "asset_class": "crypto", "source": "yahoo"},
    {"symbol": "SOL-USD", "name": "Solana", "asset_class": "crypto", "source": "yahoo"},
    # US Indices
    {"symbol": "^GSPC", "name": "S&P 500", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^DJI", "name": "Dow Jones", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^IXIC", "name": "NASDAQ", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^RUT", "name": "Russell 2000", "asset_class": "index", "source": "yahoo"},
    # Stocks
    {"symbol": "AAPL", "name": "Apple", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "MSFT", "name": "Microsoft", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "NVDA", "name": "NVIDIA", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "JPM", "name": "JPMorgan", "asset_class": "stock", "source": "yahoo"},
    # Bonds (ETF proxies)
    {"symbol": "TLT", "name": "20+ Year Treasury", "asset_class": "bond", "source": "yahoo"},
    {"symbol": "IEF", "name": "7-10 Year Treasury", "asset_class": "bond", "source": "yahoo"},
    {"symbol": "LQD", "name": "Investment Grade Corp", "asset_class": "bond", "source": "yahoo"},
    {"symbol": "HYG", "name": "High Yield Corp", "asset_class": "bond", "source": "yahoo"},
    # Commodities
    {"symbol": "GC=F", "name": "Gold", "asset_class": "commodity", "source": "yahoo"},
    {"symbol": "SI=F", "name": "Silver", "asset_class": "commodity", "source": "yahoo"},
    {"symbol": "CL=F", "name": "Crude Oil WTI", "asset_class": "commodity", "source": "yahoo"},
    {"symbol": "NG=F", "name": "Natural Gas", "asset_class": "commodity", "source": "yahoo"},
    # Forex
    {"symbol": "EURUSD=X", "name": "EUR/USD", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "USDJPY=X", "name": "USD/JPY", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "asset_class": "forex", "source": "yahoo"},
]

# Backward-compatible alias used by older imports
MONITORED_ASSETS = DEFAULT_ASSETS

CATALOG_BY_SYMBOL = {a["symbol"].upper(): a for a in DEFAULT_ASSETS}


def lookup_asset(symbol: str) -> dict | None:
    return CATALOG_BY_SYMBOL.get(symbol.strip().upper())


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()
