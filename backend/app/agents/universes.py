"""Global region universes for scout agents."""

from __future__ import annotations

from app.agents.types import RegionClass, ScoutUniverse
from app.data.assets import DEFAULT_ASSETS, US_INDEX_SYMBOLS
from app.models.schemas import AssetClass

# Only these indices/ETFs count as US equity universe.
# Every other index (Asia, Russia, Brazil, Europe, EM baskets, …) → global_equity.
US_INDEX_ETFS = US_INDEX_SYMBOLS


def default_universes(watchlist: list[dict] | None = None) -> dict[RegionClass, ScoutUniverse]:
    source = watchlist if watchlist is not None else DEFAULT_ASSETS

    us_syms: list[str] = []
    global_syms: list[str] = []
    crypto_syms: list[str] = []
    tokenized_syms: list[str] = []
    bond_syms: list[str] = []
    cmdty_syms: list[str] = []
    fx_syms: list[str] = []

    for a in source:
        sym_u = str(a["symbol"]).upper()
        ac = a["asset_class"]
        if ac == "stock":
            us_syms.append(a["symbol"])
        elif ac == "etf":
            # Equity/crypto ETFs feed US scout desk
            us_syms.append(a["symbol"])
        elif ac == "tokenized":
            tokenized_syms.append(a["symbol"])
        elif ac == "index":
            if sym_u in US_INDEX_ETFS:
                us_syms.append(a["symbol"])
            else:
                # World indexes: Asia, Russia, Brazil, Europe, EM, …
                global_syms.append(a["symbol"])
        elif ac == "crypto":
            crypto_syms.append(a["symbol"])
        elif ac == "bond":
            bond_syms.append(a["symbol"])
        elif ac == "commodity":
            cmdty_syms.append(a["symbol"])
        elif ac == "forex":
            fx_syms.append(a["symbol"])

    # Tokenized equities: same desk as crypto venues (24/5), tracked with crypto scout
    crypto_syms.extend(tokenized_syms)

    return {
        "us_equity": ScoutUniverse(
            region="us_equity",
            asset_classes=(AssetClass.STOCK, AssetClass.INDEX, AssetClass.ETF),
            symbols=tuple(dict.fromkeys(us_syms)),
        ),
        "global_equity": ScoutUniverse(
            region="global_equity",
            asset_classes=(AssetClass.INDEX,),
            symbols=tuple(dict.fromkeys(global_syms)),
        ),
        "crypto": ScoutUniverse(
            region="crypto",
            asset_classes=(AssetClass.CRYPTO, AssetClass.TOKENIZED),
            symbols=tuple(dict.fromkeys(crypto_syms)),
        ),
        "bonds": ScoutUniverse(
            region="bonds",
            asset_classes=(AssetClass.BOND,),
            symbols=tuple(dict.fromkeys(bond_syms)),
        ),
        "commodities": ScoutUniverse(
            region="commodities",
            asset_classes=(AssetClass.COMMODITY,),
            symbols=tuple(dict.fromkeys(cmdty_syms)),
        ),
        "forex": ScoutUniverse(
            region="forex",
            asset_classes=(AssetClass.FOREX,),
            symbols=tuple(dict.fromkeys(fx_syms)),
        ),
    }
