"""Default instrument catalog and helpers for the watchlist."""

from __future__ import annotations

# UI / API region ids (Polish labels live in REGION_LABELS).
RegionId = str

US_INDEX_SYMBOLS = {
    "^GSPC",
    "^DJI",
    "^IXIC",
    "^RUT",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
}

AMERICAS_SYMBOLS = {
    "^GSPTSE",
    "^BVSP",
    "^MXX",
    "^IPSA",
    "EWZ",
    "EWC",
    "EWW",
}

EUROPE_SYMBOLS = {
    "^FTSE",
    "^GDAXI",
    "^FCHI",
    "^STOXX50E",
    "^IBEX",
    "^AEX",
    "^SSMI",
    "^OMXSPI",
    "WIG20.WA",
    "EWG",
    "EWU",
    "EZU",
}

RUSSIA_SYMBOLS = {
    "IMOEX.ME",
    "RTSI.ME",
    "ERUS",
    "RSX",
    "SBER.ME",
    "GAZP.ME",
}

ASIA_SYMBOLS = {
    "^N225",
    "^HSI",
    "000001.SS",
    "399001.SZ",
    "^KS11",
    "^TWII",
    "^BSESN",
    "^NSEI",
    "^STI",
    "^JKSE",
    "^KLSE",
    "^AXJO",
    "^NZ50",
    "EWJ",
    "FXI",
    "MCHI",
    "EWY",
    "EWT",
    "INDA",
    "EWA",
}

MEA_SYMBOLS = {
    "^TA125.TA",
    "^CASE30",
    "^J203.JO",
    "EZA",
}

WORLD_EM_SYMBOLS = {
    "EFA",
    "EEM",
    "VXUS",
    "IEFA",
    "ACWX",
    "VWO",
    "IEMG",
}

# Removed / broken Yahoo tickers — dropped from watchlist on DB merge.
RETIRED_SYMBOLS = {"JN0U.JO"}

REGION_LABELS: dict[str, str] = {
    "usa": "USA",
    "americas": "Ameryka (Brazylia+)",
    "europe": "Europa",
    "russia": "Rosja",
    "asia": "Azja–Pacyfik",
    "mea": "MEA / Afryka",
    "world": "Świat / EM",
    "crypto": "Krypto",
    "bonds": "Obligacje",
    "commodities": "Surowce",
    "forex": "Forex",
}

# Regions that count as "rynki globalne" (non-US equity / indexes).
GLOBAL_MARKET_REGIONS = frozenset(
    {"americas", "europe", "russia", "asia", "mea", "world"}
)

DEFAULT_ASSETS: list[dict] = [
    # ── Crypto ──────────────────────────────────────────────────────────
    {"symbol": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto", "source": "yahoo"},
    {"symbol": "ETH-USD", "name": "Ethereum", "asset_class": "crypto", "source": "yahoo"},
    {"symbol": "SOL-USD", "name": "Solana", "asset_class": "crypto", "source": "yahoo"},
    # ── US indices + liquid ETFs ────────────────────────────────────────
    {"symbol": "^GSPC", "name": "S&P 500", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^DJI", "name": "Dow Jones", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^IXIC", "name": "NASDAQ", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^RUT", "name": "Russell 2000", "asset_class": "index", "source": "yahoo"},
    {"symbol": "SPY", "name": "SPDR S&P 500", "asset_class": "index", "source": "yahoo"},
    {"symbol": "QQQ", "name": "Invesco QQQ", "asset_class": "index", "source": "yahoo"},
    {"symbol": "IWM", "name": "iShares Russell 2000", "asset_class": "index", "source": "yahoo"},
    {"symbol": "DIA", "name": "SPDR Dow Jones", "asset_class": "index", "source": "yahoo"},
    # ── Americas (ex-US) — Brazylia, Kanada, Meksyk, Chile ─────────────
    {"symbol": "^GSPTSE", "name": "Canada TSX", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^BVSP", "name": "Brazil Bovespa", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^MXX", "name": "Mexico IPC", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^IPSA", "name": "Chile IPSA", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWZ", "name": "iShares Brazil", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWC", "name": "iShares Canada", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWW", "name": "iShares Mexico", "asset_class": "index", "source": "yahoo"},
    # ── Europe ──────────────────────────────────────────────────────────
    {"symbol": "^FTSE", "name": "FTSE 100 UK", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^GDAXI", "name": "DAX Germany", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^FCHI", "name": "CAC 40 France", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^STOXX50E", "name": "Euro Stoxx 50", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^IBEX", "name": "IBEX 35 Spain", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^AEX", "name": "AEX Netherlands", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^SSMI", "name": "SMI Switzerland", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^OMXSPI", "name": "OMX Stockholm", "asset_class": "index", "source": "yahoo"},
    {"symbol": "WIG20.WA", "name": "WIG20 Poland", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWG", "name": "iShares Germany", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWU", "name": "iShares UK", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EZU", "name": "iShares Eurozone", "asset_class": "index", "source": "yahoo"},
    # ── Russia / CIS ────────────────────────────────────────────────────
    {"symbol": "IMOEX.ME", "name": "MOEX Russia", "asset_class": "index", "source": "yahoo"},
    {"symbol": "RTSI.ME", "name": "RTS Russia", "asset_class": "index", "source": "yahoo"},
    {"symbol": "ERUS", "name": "iShares Russia", "asset_class": "index", "source": "yahoo"},
    {"symbol": "RSX", "name": "VanEck Russia", "asset_class": "index", "source": "yahoo"},
    {"symbol": "SBER.ME", "name": "Sberbank", "asset_class": "index", "source": "yahoo"},
    {"symbol": "GAZP.ME", "name": "Gazprom", "asset_class": "index", "source": "yahoo"},
    # ── Asia–Pacific ────────────────────────────────────────────────────
    {"symbol": "^N225", "name": "Nikkei 225 Japan", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^HSI", "name": "Hang Seng HK", "asset_class": "index", "source": "yahoo"},
    {"symbol": "000001.SS", "name": "Shanghai Composite", "asset_class": "index", "source": "yahoo"},
    {"symbol": "399001.SZ", "name": "Shenzhen Component", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^KS11", "name": "KOSPI Korea", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^TWII", "name": "Taiwan Weighted", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^BSESN", "name": "Sensex India", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^NSEI", "name": "Nifty 50 India", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^STI", "name": "STI Singapore", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^JKSE", "name": "Jakarta Composite", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^KLSE", "name": "FTSE Malaysia", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^AXJO", "name": "ASX 200 Australia", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^NZ50", "name": "NZX 50", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWJ", "name": "iShares Japan", "asset_class": "index", "source": "yahoo"},
    {"symbol": "FXI", "name": "iShares China Large-Cap", "asset_class": "index", "source": "yahoo"},
    {"symbol": "MCHI", "name": "iShares MSCI China", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWY", "name": "iShares Korea", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWT", "name": "iShares Taiwan", "asset_class": "index", "source": "yahoo"},
    {"symbol": "INDA", "name": "iShares India", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EWA", "name": "iShares Australia", "asset_class": "index", "source": "yahoo"},
    # ── Middle East / Africa ────────────────────────────────────────────
    {"symbol": "^TA125.TA", "name": "TA-125 Israel", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^CASE30", "name": "EGX 30 Egypt", "asset_class": "index", "source": "yahoo"},
    {"symbol": "^J203.JO", "name": "FTSE/JSE Top 40", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EZA", "name": "iShares South Africa", "asset_class": "index", "source": "yahoo"},
    # ── Global / EM baskets ─────────────────────────────────────────────
    {"symbol": "EFA", "name": "iShares MSCI EAFE", "asset_class": "index", "source": "yahoo"},
    {"symbol": "EEM", "name": "iShares MSCI Emerging", "asset_class": "index", "source": "yahoo"},
    {"symbol": "VXUS", "name": "Vanguard Total Intl", "asset_class": "index", "source": "yahoo"},
    {"symbol": "IEFA", "name": "iShares Core EAFE", "asset_class": "index", "source": "yahoo"},
    {"symbol": "ACWX", "name": "iShares MSCI ACWI ex-US", "asset_class": "index", "source": "yahoo"},
    {"symbol": "VWO", "name": "Vanguard Emerging Mkts", "asset_class": "index", "source": "yahoo"},
    {"symbol": "IEMG", "name": "iShares Core MSCI EM", "asset_class": "index", "source": "yahoo"},
    # ── US stocks ───────────────────────────────────────────────────────
    {"symbol": "AAPL", "name": "Apple", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "MSFT", "name": "Microsoft", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "NVDA", "name": "NVIDIA", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "JPM", "name": "JPMorgan", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "TSLA", "name": "Tesla", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "AMZN", "name": "Amazon", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "META", "name": "Meta", "asset_class": "stock", "source": "yahoo"},
    {"symbol": "GOOGL", "name": "Alphabet", "asset_class": "stock", "source": "yahoo"},
    # ── Bonds ───────────────────────────────────────────────────────────
    {"symbol": "TLT", "name": "20+ Year Treasury", "asset_class": "bond", "source": "yahoo"},
    {"symbol": "IEF", "name": "7-10 Year Treasury", "asset_class": "bond", "source": "yahoo"},
    {"symbol": "LQD", "name": "Investment Grade Corp", "asset_class": "bond", "source": "yahoo"},
    {"symbol": "HYG", "name": "High Yield Corp", "asset_class": "bond", "source": "yahoo"},
    # ── Commodities ─────────────────────────────────────────────────────
    {"symbol": "GC=F", "name": "Gold", "asset_class": "commodity", "source": "yahoo"},
    {"symbol": "SI=F", "name": "Silver", "asset_class": "commodity", "source": "yahoo"},
    {"symbol": "CL=F", "name": "Crude Oil WTI", "asset_class": "commodity", "source": "yahoo"},
    {"symbol": "NG=F", "name": "Natural Gas", "asset_class": "commodity", "source": "yahoo"},
    # ── Forex ───────────────────────────────────────────────────────────
    {"symbol": "EURUSD=X", "name": "EUR/USD", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "USDJPY=X", "name": "USD/JPY", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "USDBRL=X", "name": "USD/BRL", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "USDCNY=X", "name": "USD/CNY", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "USDRUB=X", "name": "USD/RUB", "asset_class": "forex", "source": "yahoo"},
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "asset_class": "forex", "source": "yahoo"},
]

# Backward-compatible alias used by older imports
MONITORED_ASSETS = DEFAULT_ASSETS

CATALOG_BY_SYMBOL = {a["symbol"].upper(): a for a in DEFAULT_ASSETS}


def lookup_asset(symbol: str) -> dict | None:
    return CATALOG_BY_SYMBOL.get(symbol.strip().upper())


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def resolve_region(asset: dict) -> str:
    """Map an asset to a UI/API region bucket."""
    ac = str(asset.get("asset_class", "")).lower()
    if ac == "crypto":
        return "crypto"
    if ac == "bond":
        return "bonds"
    if ac == "commodity":
        return "commodities"
    if ac == "forex":
        return "forex"
    if ac == "stock":
        return "usa"

    sym = str(asset.get("symbol", "")).upper()
    if sym in US_INDEX_SYMBOLS:
        return "usa"
    if sym in RUSSIA_SYMBOLS:
        return "russia"
    if sym in ASIA_SYMBOLS:
        return "asia"
    if sym in EUROPE_SYMBOLS:
        return "europe"
    if sym in AMERICAS_SYMBOLS:
        return "americas"
    if sym in MEA_SYMBOLS:
        return "mea"
    if sym in WORLD_EM_SYMBOLS:
        return "world"
    # Unknown indexes → treat as global basket
    if ac == "index":
        return "world"
    return "usa"


def enrich_asset(asset: dict) -> dict:
    """Return a shallow copy with region + label filled in."""
    out = dict(asset)
    region = resolve_region(out)
    out["region"] = region
    out["region_label"] = REGION_LABELS.get(region, region)
    return out


def is_global_market(asset: dict) -> bool:
    return resolve_region(asset) in GLOBAL_MARKET_REGIONS
