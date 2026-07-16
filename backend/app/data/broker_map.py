"""Educational broker / venue hints for where an instrument can typically be bought.

Not a recommendation or affiliate link — informational only for paper-trading context.
"""

from __future__ import annotations

from typing import Any

# name, regions (ISO-ish tags), url, notes, asset_classes covered
_BROKERS: dict[str, dict[str, Any]] = {
    "ibkr": {
        "id": "ibkr",
        "name": "Interactive Brokers",
        "regions": ["global", "us", "eu", "asia", "pl"],
        "url": "https://www.interactivebrokers.com/",
        "notes": "Global stocks, ETFs, futures, forex",
        "asset_classes": ["stock", "etf", "index", "bond", "commodity", "forex"],
    },
    "xtb": {
        "id": "xtb",
        "name": "XTB",
        "regions": ["pl", "eu"],
        "url": "https://www.xtb.com/",
        "notes": "CFD + stocks/ETFs (PL/EU)",
        "asset_classes": ["stock", "etf", "index", "commodity", "forex", "crypto"],
    },
    "degiro": {
        "id": "degiro",
        "name": "DEGIRO",
        "regions": ["eu", "pl"],
        "url": "https://www.degiro.com/",
        "notes": "EU/US equities & ETFs",
        "asset_classes": ["stock", "etf", "bond"],
    },
    "revolut": {
        "id": "revolut",
        "name": "Revolut",
        "regions": ["eu", "pl", "us"],
        "url": "https://www.revolut.com/",
        "notes": "Fractional US/EU shares",
        "asset_classes": ["stock", "etf", "crypto"],
    },
    "binance": {
        "id": "binance",
        "name": "Binance",
        "regions": ["global"],
        "url": "https://www.binance.com/",
        "notes": "Spot & derivatives crypto",
        "asset_classes": ["crypto"],
    },
    "kraken": {
        "id": "kraken",
        "name": "Kraken",
        "regions": ["global", "us", "eu"],
        "url": "https://www.kraken.com/",
        "notes": "Spot crypto",
        "asset_classes": ["crypto"],
    },
    "coinbase": {
        "id": "coinbase",
        "name": "Coinbase",
        "regions": ["us", "eu", "global"],
        "url": "https://www.coinbase.com/",
        "notes": "Spot crypto (US-friendly)",
        "asset_classes": ["crypto"],
    },
    "bos": {
        "id": "bos",
        "name": "BOŚ Bank",
        "regions": ["pl"],
        "url": "https://bossa.pl/",
        "notes": "GPW / NewConnect",
        "asset_classes": ["stock", "etf", "bond"],
    },
    "mbank": {
        "id": "mbank",
        "name": "mBank eMAKLER",
        "regions": ["pl"],
        "url": "https://www.mbank.pl/",
        "notes": "GPW brokerage",
        "asset_classes": ["stock", "etf", "bond"],
    },
}

_SYMBOL_OVERRIDES: dict[str, list[str]] = {
    "BTC-USD": ["binance", "kraken", "coinbase", "xtb"],
    "ETH-USD": ["binance", "kraken", "coinbase", "xtb"],
    "PKN.WA": ["xtb", "bos", "mbank", "ibkr"],
    "CDR.WA": ["xtb", "bos", "mbank", "ibkr"],
    "KGH.WA": ["xtb", "bos", "mbank", "ibkr"],
    "PZU.WA": ["xtb", "bos", "mbank", "ibkr"],
    "ALE.WA": ["xtb", "bos", "mbank", "ibkr"],
    "XTB.WA": ["bos", "mbank", "ibkr", "degiro"],
}


def primary_exchange(symbol: str, asset_class: str | None = None) -> str:
    if symbol.endswith("-USD"):
        return "CRYPTO / Binance-style"
    if symbol.endswith(".WA"):
        return "GPW (Warsaw)"
    if symbol.endswith(".KS"):
        return "KRX (Korea)"
    if symbol.endswith(".T"):
        return "TSE (Tokyo)"
    if symbol.endswith(".PA"):
        return "Euronext Paris"
    if symbol.endswith(".SW"):
        return "SIX Swiss"
    if symbol.endswith(".TA"):
        return "TASE"
    if symbol.endswith(".SS"):
        return "SSE Shanghai"
    if symbol.endswith(".L"):
        return "LSE"
    if symbol.endswith(".DE") or symbol.endswith(".F"):
        return "XETRA / Frankfurt"
    if symbol.startswith("^"):
        return "Index (ETF/CFD proxy)"
    if "=X" in symbol or asset_class == "forex":
        return "FX (spot / CFD)"
    if asset_class == "commodity":
        return "Futures / commodity ETF"
    nasdaq = {
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA",
        "AVGO", "COST", "NFLX", "AMD", "INTC", "ADBE", "PYPL", "QCOM",
        "RKLB", "IRDM", "ASTS", "GSAT", "ON", "ARKX",
    }
    if symbol in nasdaq:
        return "NASDAQ"
    return "NYSE / US listed"


def _broker_ids_for(symbol: str, asset_class: str, region: str | None) -> list[str]:
    if symbol in _SYMBOL_OVERRIDES:
        return list(_SYMBOL_OVERRIDES[symbol])

    if symbol.endswith("-USD") or asset_class == "crypto":
        return ["binance", "kraken", "coinbase", "xtb"]

    if symbol.endswith(".WA") or region == "pl":
        return ["xtb", "bos", "mbank", "ibkr"]

    if region in ("eu",) or any(symbol.endswith(s) for s in (".PA", ".DE", ".F", ".L", ".SW", ".AS", ".MI")):
        return ["degiro", "xtb", "ibkr", "revolut"]

    if asset_class == "forex":
        return ["xtb", "ibkr"]

    if asset_class in ("commodity", "index", "bond"):
        return ["ibkr", "xtb", "degiro"]

    # Default US / global equity
    return ["ibkr", "xtb", "degiro", "revolut"]


def resolve_broker_info(
    symbol: str,
    asset_class: str = "stock",
    region: str | None = None,
) -> dict[str, Any]:
    ids = _broker_ids_for(symbol, asset_class, region)
    brokers = []
    for bid in ids:
        meta = _BROKERS.get(bid)
        if not meta:
            continue
        brokers.append(
            {
                "id": meta["id"],
                "name": meta["name"],
                "regions": list(meta["regions"]),
                "url": meta["url"],
                "notes": meta["notes"],
            }
        )
    return {
        "primary_exchange": primary_exchange(symbol, asset_class),
        "brokers": brokers,
        "disclaimer": "Informacja edukacyjna — nie rekomendacja. Sprawdź dostępność instrumentu i lokalne przepisy u brokera.",
    }
