"""Resolve coin / instrument logo URLs for paper positions and UI."""

from __future__ import annotations

CRYPTO_ICON_CDN = "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/32/color"

# Yahoo / desk symbols → cryptocurrency-icons slug
_CRYPTO_SLUGS: dict[str, str] = {
    "BTC-USD": "btc",
    "ETH-USD": "eth",
    "SOL-USD": "sol",
    "BNB-USD": "bnb",
    "XRP-USD": "xrp",
    "ADA-USD": "ada",
    "DOGE-USD": "doge",
    "AVAX-USD": "avax",
    "LINK-USD": "link",
    "DOT-USD": "dot",
    "MATIC-USD": "matic",
    "POL-USD": "matic",
    "LTC-USD": "ltc",
    "ATOM-USD": "atom",
    "NEAR-USD": "near",
    "APT-USD": "apt",
    "ARB-USD": "arb",
    "OP-USD": "op",
    "SUI-USD": "sui",
    "PEPE-USD": "pepe",
    "SHIB-USD": "shib",
    "UNI-USD": "uni",
    "AAVE-USD": "aave",
    "MKR-USD": "mkr",
    "CRV-USD": "crv",
    "TRX-USD": "trx",
    "TON-USD": "ton",
    "HBAR-USD": "hbar",
    "FIL-USD": "fil",
    "ICP-USD": "icp",
    "RENDER-USD": "rndr",
    "INJ-USD": "inj",
    "SEI-USD": "sei",
    "WIF-USD": "wif",
    "BONK-USD": "bonk",
}


def resolve_coin_image_url(symbol: str, asset_class: str | None = None) -> str | None:
    """Best-effort public icon URL. Frontend falls back to initials if broken."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    ac = (asset_class or "").strip().lower()

    if sym in _CRYPTO_SLUGS:
        return f"{CRYPTO_ICON_CDN}/{_CRYPTO_SLUGS[sym]}.png"

    # Bare ticker crypto (BTC, ETH) or -USD pair
    base = sym.split("-")[0].split("/")[0].strip().lower()
    if ac == "crypto" or sym.endswith("-USD"):
        if len(base) <= 6 and base.isalnum():
            return f"{CRYPTO_ICON_CDN}/{base}.png"

    return None
