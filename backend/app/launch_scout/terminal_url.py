"""Terminal / exchange deep-links for launch candidates (Solana → Axiom)."""

from __future__ import annotations

import re
from urllib.parse import urlencode

# Fake pair suffixes we accidentally stored (mint:4meme) — never send to DexScreener
_BAD_PAIR_SUFFIX = re.compile(r":(4meme|flap|pump|pumpfun|bonding)$", re.I)
_HEX_ADDR = re.compile(r"^(0x)?[0-9a-fA-F]{40}$")
_SOL_MINT = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _norm_chain(chain: str | None) -> str:
    c = (chain or "").lower().strip()
    if c in ("sol", "solana"):
        return "solana"
    if c in ("bsc", "bnb", "binance"):
        return "bsc"
    if c in ("eth", "ethereum"):
        return "ethereum"
    return c or "solana"


def sanitize_address(value: str | None) -> str:
    """Strip junk suffixes like `:4meme` from mint/pair fields."""
    raw = (value or "").strip()
    if not raw:
        return ""
    cleaned = _BAD_PAIR_SUFFIX.sub("", raw).strip()
    # Also drop accidental `chain:mint` if someone passed candidate_id
    if ":" in cleaned and not cleaned.startswith("0x"):
        # solana mint never has colon; bsc candidate_id is chain:0x…
        parts = cleaned.split(":")
        if len(parts) == 2 and parts[0] in ("bsc", "solana", "ethereum", "base", "sol", "eth"):
            cleaned = parts[1]
    return cleaned


_AXIOM_CHAINS = frozenset({"solana", "bsc", "ethereum", "robinhood"})
_AXIOM_CHAIN_CODE = {
    "solana": "sol",
    "bsc": "bnb",
    "ethereum": "eth",
    "robinhood": "robinhood",
}


def axiom_meme_url(mint: str, chain: str = "solana") -> str:
    """Chain-aware Axiom meme terminal deep link."""
    ch = _norm_chain(chain)
    axiom_chain = _AXIOM_CHAIN_CODE.get(ch, "sol")
    q = urlencode({"chain": axiom_chain, "pulseChains": axiom_chain})
    return f"https://axiom.trade/meme/{mint}?{q}"


def _uses_axiom_terminal(chain: str) -> bool:
    return _norm_chain(chain) in _AXIOM_CHAINS


def is_plausible_address(addr: str, chain: str = "") -> bool:
    a = sanitize_address(addr)
    if not a:
        return False
    ch = _norm_chain(chain)
    if ch in ("bsc", "ethereum", "base", "arbitrum", "polygon", "optimism", "blast"):
        return bool(_HEX_ADDR.match(a))
    if ch == "solana":
        return bool(_SOL_MINT.match(a)) and ":" not in a
    return ":" not in a and len(a) >= 8


def terminal_url(
    *,
    mint: str = "",
    symbol: str = "",
    chain: str = "",
    pair_address: str = "",
    existing_url: str = "",
    source: str = "",
    prefer_launchpad: bool = False,
) -> str:
    """Primary click target: Axiom meme terminal for Solana, DexScreener otherwise."""
    mint = sanitize_address(mint)
    symbol = (symbol or "").strip()
    pair = sanitize_address(pair_address)
    ch = _norm_chain(chain)
    existing = (existing_url or "").strip()
    src = (source or "").lower()

    # Bonding 4meme without a real DS pair → four.meme (DexScreener 404s on mint:4meme)
    if prefer_launchpad or (src in ("4meme", "four") and not pair):
        if mint and ("4meme" in src or "four" in src):
            return f"https://four.meme/token/{mint}"

    if _uses_axiom_terminal(ch) and mint and is_plausible_address(mint, ch):
        return axiom_meme_url(mint, ch)

    path = pair if pair and is_plausible_address(pair, ch) else mint
    if path and is_plausible_address(path, ch):
        return f"https://dexscreener.com/{ch}/{path}"

    q = mint or symbol
    if q:
        if ch == "solana":
            return f"https://axiom.trade/?q={q}"
        return f"https://dexscreener.com/search?q={q}"
    if existing.startswith("http") and ":4meme" not in existing and "%3A4meme" not in existing.lower():
        return existing
    return ""


def ensure_candidate_urls(c: dict) -> dict:
    """Mutate candidate dict so addresses/URLs are clean exchange terminals."""
    mint = sanitize_address(str(c.get("mint") or ""))
    pair = sanitize_address(str(c.get("pair_address") or ""))
    if mint:
        c["mint"] = mint

    src = str(c.get("source") or c.get("dex_id") or "").lower()
    tags = {str(t).lower() for t in (c.get("tags") or [])}
    # Detect bonding before deciding whether mint-as-pair is real
    bonding = ("bonding" in tags) or (src in ("4meme", "flap", "pump") and not pair)

    # Never persist fake mint:4meme pairs
    if pair and is_plausible_address(pair, str(c.get("chain") or "")):
        if bonding and mint and pair.lower() == mint.lower():
            c["pair_address"] = ""
            bonding = True
        else:
            c["pair_address"] = pair
            bonding = ("bonding" in tags) or (src in ("4meme", "flap", "pump") and not c["pair_address"])
    else:
        c["pair_address"] = ""
        bonding = ("bonding" in tags) or (src in ("4meme", "flap", "pump"))

    url = terminal_url(
        mint=mint,
        symbol=str(c.get("symbol") or ""),
        chain=str(c.get("chain") or ""),
        pair_address=c.get("pair_address") or "",
        existing_url=str(c.get("url") or ""),
        source=src,
        prefer_launchpad=bonding and ("4meme" in tags or "4meme" in src),
    )
    if url:
        c["url"] = url
        c["terminal_url"] = url
        if mint and ("4meme" in src or "four" in src or "4meme" in tags):
            c["launchpad_url"] = f"https://four.meme/token/{mint}"
        elif mint and ("pump" in src or "pump" in tags):
            c["launchpad_url"] = f"https://pump.fun/{mint}"
    return c
