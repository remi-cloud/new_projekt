"""Official / best-effort community links per instrument.

Every symbol gets at least an X URL (official profile or search fallback).
Static map covers the catalog core; tokenized xStocks inherit underlying stock links.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

# symbol (Yahoo/catalog) → optional official community URLs
# Keys: x | telegram | discord | website | x_community
_COMMUNITY_MAP: dict[str, dict[str, str]] = {
    # ── Crypto L1 / majors ──
    "BTC-USD": {
        "x": "https://x.com/bitcoin",
        "website": "https://bitcoin.org",
    },
    "ETH-USD": {
        "x": "https://x.com/ethereum",
        "discord": "https://discord.gg/ethereum-org",
        "website": "https://ethereum.org",
    },
    "SOL-USD": {
        "x": "https://x.com/solana",
        "discord": "https://discord.gg/solana",
        "website": "https://solana.com",
    },
    "BNB-USD": {
        "x": "https://x.com/bnbchain",
        "website": "https://www.bnbchain.org",
    },
    "XRP-USD": {
        "x": "https://x.com/Ripple",
        "website": "https://ripple.com",
    },
    "ADA-USD": {
        "x": "https://x.com/Cardano",
        "website": "https://cardano.org",
    },
    "DOGE-USD": {
        "x": "https://x.com/dogecoin",
        "website": "https://dogecoin.com",
    },
    "AVAX-USD": {
        "x": "https://x.com/avax",
        "website": "https://www.avax.network",
    },
    "LINK-USD": {
        "x": "https://x.com/chainlink",
        "website": "https://chain.link",
    },
    "DOT-USD": {
        "x": "https://x.com/Polkadot",
        "website": "https://polkadot.network",
    },
    # ── Mag7 / US stocks ──
    "AAPL": {"x": "https://x.com/Apple", "website": "https://www.apple.com"},
    "MSFT": {"x": "https://x.com/Microsoft", "website": "https://www.microsoft.com"},
    "GOOGL": {"x": "https://x.com/Google", "website": "https://abc.xyz"},
    "AMZN": {"x": "https://x.com/amazon", "website": "https://www.amazon.com"},
    "NVDA": {"x": "https://x.com/nvidia", "website": "https://www.nvidia.com"},
    "META": {"x": "https://x.com/Meta", "website": "https://about.meta.com"},
    "TSLA": {"x": "https://x.com/Tesla", "website": "https://www.tesla.com"},
    "JPM": {"x": "https://x.com/jpmorgan", "website": "https://www.jpmorganchase.com"},
    "V": {"x": "https://x.com/Visa", "website": "https://www.visa.com"},
    "XOM": {"x": "https://x.com/exxonmobil", "website": "https://corporate.exxonmobil.com"},
    "COIN": {"x": "https://x.com/coinbase", "website": "https://www.coinbase.com"},
    "MSTR": {"x": "https://x.com/MicroStrategy", "website": "https://www.microstrategy.com"},
    "GME": {"x": "https://x.com/GameStop", "website": "https://www.gamestop.com"},
    "HOOD": {"x": "https://x.com/RobinhoodApp", "website": "https://robinhood.com"},
    "PLTR": {"x": "https://x.com/PalantirTech", "website": "https://www.palantir.com"},
    "AMD": {"x": "https://x.com/AMD", "website": "https://www.amd.com"},
    "INTC": {"x": "https://x.com/intel", "website": "https://www.intel.com"},
    "NFLX": {"x": "https://x.com/netflix", "website": "https://www.netflix.com"},
    "BA": {"x": "https://x.com/Boeing", "website": "https://www.boeing.com"},
    "LMT": {"x": "https://x.com/LockheedMartin", "website": "https://www.lockheedmartin.com"},
    "RKLB": {"x": "https://x.com/RocketLab", "website": "https://www.rocketlabusa.com"},
    "ASTS": {"x": "https://x.com/AST_SpaceMobile", "website": "https://ast-science.com"},
    "TSM": {"x": "https://x.com/TSMC_News", "website": "https://www.tsmc.com"},
    "BABA": {"x": "https://x.com/AlibabaGroup", "website": "https://www.alibabagroup.com"},
    "ASML": {"x": "https://x.com/ASMLcompany", "website": "https://www.asml.com"},
    "SAP": {"x": "https://x.com/SAP", "website": "https://www.sap.com"},
    # ── PL ──
    "PKN.WA": {"x": "https://x.com/ORLEN", "website": "https://www.orlen.pl"},
    "PKO.WA": {"x": "https://x.com/PKOBP", "website": "https://www.pkobp.pl"},
    "PZU.WA": {"website": "https://www.pzu.pl"},
    # ── Crypto ETFs → parent community ──
    "IBIT": {"x": "https://x.com/bitcoin", "website": "https://www.ishares.com"},
    "FBTC": {"x": "https://x.com/bitcoin", "website": "https://www.fidelity.com"},
    "ARKB": {"x": "https://x.com/ARKinvest", "website": "https://www.ark-funds.com"},
    "BITO": {"x": "https://x.com/ProShares", "website": "https://www.proshares.com"},
    "ETHA": {"x": "https://x.com/ethereum", "website": "https://www.ishares.com"},
    "ETHE": {"x": "https://x.com/Grayscale", "website": "https://grayscale.com"},
    "GBTC": {"x": "https://x.com/Grayscale", "website": "https://grayscale.com"},
    # ── Indices (search-friendly official-ish) ──
    "^GSPC": {"x": "https://x.com/SPDJIndices", "website": "https://www.spglobal.com/spdji"},
    "^IXIC": {"x": "https://x.com/Nasdaq", "website": "https://www.nasdaq.com"},
    "^DJI": {"x": "https://x.com/DowJones", "website": "https://www.dowjones.com"},
}


def _norm_symbol(symbol: str | None) -> str:
    return (symbol or "").strip().upper()


def _search_ticker(symbol: str) -> str:
    """Human-friendly query fragment for X search."""
    s = _norm_symbol(symbol)
    if s.endswith("-USD"):
        return s[:-4]
    if s.endswith("X-USD") and len(s) > 5:
        # AAPLX-USD → AAPL
        return s[:-5]
    if s.startswith("^"):
        return s[1:]
    return s


def _x_search_url(symbol: str, name: str | None = None) -> str:
    q = _search_ticker(symbol)
    if name:
        # Prefer short name tokens without parentheticals
        clean = name.split("(")[0].strip()
        if clean and len(clean) < 40:
            q = f"{q} OR {clean}"
    return f"https://x.com/search?q={quote_plus(q)}&f=live"


def _underlying_symbol(symbol: str) -> str | None:
    """Map tokenized xStock → equity ticker when present in catalog."""
    try:
        from app.data.assets import lookup_asset

        meta = lookup_asset(symbol) or {}
        und = meta.get("underlying")
        if isinstance(und, str) and und.strip():
            return und.strip().upper()
    except Exception:
        pass
    s = _norm_symbol(symbol)
    if s.endswith("X-USD") and len(s) > 5:
        return s[:-5]
    return None


def resolve_community_links(
    symbol: str,
    name: str | None = None,
    asset_class: str | None = None,
) -> dict[str, Any]:
    """Return community URLs; always includes `x` (official or search fallback)."""
    sym = _norm_symbol(symbol)
    mapped = dict(_COMMUNITY_MAP.get(sym) or {})

    if not mapped:
        und = _underlying_symbol(sym)
        if und and und in _COMMUNITY_MAP:
            mapped = dict(_COMMUNITY_MAP[und])

    x = mapped.get("x") or _x_search_url(sym, name)
    out: dict[str, Any] = {
        "x": x,
        "x_official": bool(mapped.get("x")),
        "telegram": mapped.get("telegram"),
        "discord": mapped.get("discord"),
        "website": mapped.get("website"),
        "x_community": mapped.get("x_community"),
    }
    # Drop empty optionals for cleaner JSON
    return {k: v for k, v in out.items() if v is not None and v != ""}


def community_for_assessment(symbol: str, name: str | None = None) -> dict[str, Any]:
    return resolve_community_links(symbol, name)
