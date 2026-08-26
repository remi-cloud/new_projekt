"""Axiom Pulse feeders — optional axiom.trade session + DexScreener fallback."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.launch_scout.terminal_url import axiom_meme_url, terminal_url

logger = logging.getLogger(__name__)

AXIOM_TRENDING = "https://api3.axiom.trade/new-trending-v2"
DS_BASE = "https://api.dexscreener.com"
SOL_RPC = "https://api.mainnet-beta.solana.com"
HTTP_TIMEOUT = 25.0
UA = "CyclicalTrader-AxiomDesk/1.0"


def axiom_auth_configured() -> bool:
    return bool(
        (getattr(settings, "axiom_access_token", "") or "").strip()
        and (getattr(settings, "axiom_refresh_token", "") or "").strip()
    )


def tracked_wallets() -> list[str]:
    raw = (getattr(settings, "axiom_wallets", "") or "").strip()
    out: list[str] = []
    if raw:
        for part in raw.replace(";", ",").split(","):
            w = part.strip()
            if w and w not in out:
                out.append(w)
    kar = kar_digital_wallet()
    if kar and kar not in out:
        out.insert(0, kar)
    return out[:40]


def kar_digital_wallet() -> str:
    return (getattr(settings, "kar_digital_wallet", "") or "").strip()


def wallet_owner_kind(wallet: str) -> str:
    kar = kar_digital_wallet()
    if kar and wallet == kar:
        return "kar_digital"
    return "wallet"


def wallet_owner_label(wallet: str) -> str:
    if wallet_owner_kind(wallet) == "kar_digital":
        return "Kar Digital"
    return wallet


def _fnum(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


async def fetch_axiom_trending(time_period: str = "1h") -> list[dict]:
    """Authenticated Pulse-style trending from axiom.trade (optional)."""
    if not axiom_auth_configured():
        return []
    access = (getattr(settings, "axiom_access_token", "") or "").strip()
    refresh = (getattr(settings, "axiom_refresh_token", "") or "").strip()
    cookies = {
        "auth-access-token": access,
        "auth-refresh-token": refresh,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": UA,
        "Origin": "https://axiom.trade",
        "Referer": "https://axiom.trade/",
    }
    params = {"timePeriod": time_period}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, cookies=cookies) as client:
            r = await client.get(AXIOM_TRENDING, params=params, headers=headers)
            if r.status_code >= 400:
                logger.warning("Axiom trending HTTP %s: %s", r.status_code, r.text[:200])
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("Axiom trending failed: %s", exc)
        return []

    rows: list = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("tokens", "data", "trending"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mint = str(
            row.get("tokenAddress")
            or row.get("token_address")
            or row.get("mint")
            or row.get("address")
            or ""
        ).strip()
        if not mint:
            continue
        symbol = str(row.get("tokenTicker") or row.get("symbol") or row.get("ticker") or "?").strip()
        name = str(row.get("tokenName") or row.get("name") or symbol).strip()
        out.append(
            {
                "mint": mint,
                "symbol": symbol[:32],
                "name": name[:80],
                "chain": "solana",
                "pair_address": str(row.get("pairAddress") or row.get("pair_address") or "") or None,
                "price_usd": _fnum(row.get("priceUsd") or row.get("price_usd")),
                "liquidity_usd": _fnum(row.get("liquidityUsd") or row.get("liquidity_usd")),
                "market_cap_usd": _fnum(row.get("marketCapUsd") or row.get("market_cap_usd")),
                "volume_24h": _fnum(row.get("volume24h") or row.get("volumeUsd")),
                "change_1h": _fnum(row.get("priceChange1h") or row.get("priceChange1H")),
                "change_24h": _fnum(row.get("priceChange24h") or row.get("priceChange24H")),
                "image_url": str(row.get("imageUrl") or row.get("image_url") or "") or None,
                "url": axiom_meme_url(mint, "solana"),
                "source": "axiom",
                "raw": row,
            }
        )
    return out


async def fetch_dex_pulse(limit: int = 60) -> list[dict]:
    """Public Solana Pulse stand-in via DexScreener boosts + meme search."""
    from app.launch_scout import client_dexscreener as ds

    seen: set[str] = set()
    out: list[dict] = []

    async def _add_pair(pair: dict, source: str) -> None:
        base = pair.get("baseToken") if isinstance(pair.get("baseToken"), dict) else {}
        mint = str(base.get("address") or pair.get("tokenAddress") or "").strip()
        if not mint or mint in seen:
            return
        chain = str(pair.get("chainId") or "solana").lower()
        if chain not in ("solana", "sol"):
            # Prefer Solana for Axiom desk; still keep a few multi-chain
            if len(out) > limit // 2:
                return
        seen.add(mint)
        symbol = str(base.get("symbol") or pair.get("symbol") or "?").strip()
        name = str(base.get("name") or symbol).strip()
        info = pair.get("info") if isinstance(pair.get("info"), dict) else {}
        image = None
        if isinstance(info.get("imageUrl"), str):
            image = info["imageUrl"]
        norm_chain = chain if chain != "sol" else "solana"
        pair_addr = str(pair.get("pairAddress") or "") or None
        term = terminal_url(
            mint=mint,
            symbol=symbol,
            chain=norm_chain,
            pair_address=pair_addr or "",
            existing_url=str(pair.get("url") or ""),
            source=source,
        )
        out.append(
            {
                "mint": mint,
                "symbol": symbol[:32],
                "name": name[:80],
                "chain": norm_chain,
                "pair_address": pair_addr,
                "price_usd": _fnum(pair.get("priceUsd")),
                "liquidity_usd": _fnum((pair.get("liquidity") or {}).get("usd"))
                if isinstance(pair.get("liquidity"), dict)
                else _fnum(pair.get("liquidity")),
                "market_cap_usd": _fnum(pair.get("marketCap") or pair.get("fdv")),
                "volume_24h": _fnum((pair.get("volume") or {}).get("h24"))
                if isinstance(pair.get("volume"), dict)
                else None,
                "change_1h": _fnum((pair.get("priceChange") or {}).get("h1"))
                if isinstance(pair.get("priceChange"), dict)
                else None,
                "change_24h": _fnum((pair.get("priceChange") or {}).get("h24"))
                if isinstance(pair.get("priceChange"), dict)
                else None,
                "image_url": image,
                "url": term or str(pair.get("url") or f"https://dexscreener.com/{chain}/{pair.get('pairAddress') or mint}"),
                "source": source,
                "raw": {"pairAddress": pair.get("pairAddress")},
            }
        )

    try:
        boosts = await ds.fetch_latest_boosts(limit=40)
        for b in boosts:
            chain = str(b.get("chainId") or "").lower()
            token = str(b.get("tokenAddress") or "").strip()
            if not token:
                continue
            pairs = await ds.fetch_token_pairs(chain or "solana", token)
            if pairs:
                await _add_pair(pairs[0], "dex_boost")
            elif token not in seen:
                seen.add(token)
                out.append(
                    {
                        "mint": token,
                        "symbol": str(b.get("description") or "?")[:32],
                        "name": str(b.get("description") or token)[:80],
                        "chain": chain or "solana",
                        "pair_address": None,
                        "price_usd": None,
                        "liquidity_usd": None,
                        "market_cap_usd": None,
                        "volume_24h": None,
                        "change_1h": None,
                        "change_24h": None,
                        "image_url": str(b.get("icon") or "") or None,
                        "url": axiom_meme_url(token, chain or "solana"),
                        "source": "dex_boost",
                        "raw": b,
                    }
                )
    except Exception as exc:
        logger.debug("Dex boosts pulse failed: %s", exc)

    for q in ("meme", "pump", "bonk", "sol"):
        if len(out) >= limit:
            break
        try:
            pairs = await ds.search_pairs(q, limit=15)
            for p in pairs:
                await _add_pair(p, "dex_search")
                if len(out) >= limit:
                    break
        except Exception as exc:
            logger.debug("Dex search pulse %r failed: %s", q, exc)

    return out[:limit]


async def fetch_wallet_token_accounts(wallet: str) -> list[dict]:
    """Public Solana RPC — all SPL token accounts for a wallet (best-effort)."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(SOL_RPC, json=payload, headers={"User-Agent": UA})
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("Solana RPC wallet %s… failed: %s", wallet[:8], exc)
        return []

    value = ((data.get("result") or {}) if isinstance(data, dict) else {}).get("value") or []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        parsed = (
            ((item.get("account") or {}).get("data") or {}).get("parsed")
            if isinstance(item.get("account"), dict)
            else None
        )
        if not isinstance(parsed, dict):
            continue
        info = parsed.get("info") if isinstance(parsed.get("info"), dict) else {}
        mint = str(info.get("mint") or "").strip()
        ta = info.get("tokenAmount") if isinstance(info.get("tokenAmount"), dict) else {}
        ui_amount = _fnum(ta.get("uiAmount"))
        if not mint or ui_amount is None or ui_amount <= 0:
            continue
        out.append(
            {
                "mint": mint,
                "amount": ui_amount,
                "decimals": ta.get("decimals"),
                "wallet": wallet,
            }
        )
    return out
