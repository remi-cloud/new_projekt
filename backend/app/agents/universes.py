"""Global region universes for scout agents."""

from __future__ import annotations

from app.agents.types import RegionClass, ScoutUniverse
from app.data.assets import DEFAULT_ASSETS
from app.models.schemas import AssetClass

# Only these indices/ETFs count as US equity universe.
# Every other index (Asia, Russia, Brazil, Europe, EM baskets, …) → global_equity.
US_INDEX_ETFS = {
    "^GSPC",
    "^DJI",
    "^IXIC",
    "^RUT",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
}


def default_universes(watchlist: list[dict] | None = None) -> dict[RegionClass, ScoutUniverse]:
    source = watchlist if watchlist is not None else DEFAULT_ASSETS

    us_syms: list[str] = []
    global_syms: list[str] = []
    crypto_syms: list[str] = []
    bond_syms: list[str] = []
    cmdty_syms: list[str] = []
    fx_syms: list[str] = []

    for a in source:
        sym_u = str(a["symbol"]).upper()
        ac = a["asset_class"]
        if ac == "stock":
            us_syms.append(a["symbol"])
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

    return {
        "us_equity": ScoutUniverse(
            region="us_equity",
            asset_classes=(AssetClass.STOCK, AssetClass.INDEX),
            symbols=tuple(dict.fromkeys(us_syms)),
        ),
        "global_equity": ScoutUniverse(
            region="global_equity",
            asset_classes=(AssetClass.INDEX,),
            symbols=tuple(dict.fromkeys(global_syms)),
        ),
        "crypto": ScoutUniverse(
            region="crypto",
            asset_classes=(AssetClass.CRYPTO,),
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
