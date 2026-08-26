"""GeckoTerminal feeder — new/trending pools across DEXes (best-effort)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

GT_BASE = "https://api.geckoterminal.com/api/v2"
HTTP_TIMEOUT = 18.0
UA = "CyclicalTrader-LaunchScout/1.0"

# Map Gecko network id → DexScreener-ish chainId
_NETWORK_CHAIN = {
    "solana": "solana",
    "eth": "ethereum",
    "base": "base",
    "bsc": "bsc",
    "arbitrum": "arbitrum",
    "polygon_pos": "polygon",
    "avax": "avalanche",
    "optimism": "optimism",
    "blast": "blast",
    "tron": "tron",
    "sui-network": "sui",
}

_DEFAULT_NETWORKS = (
    "solana",
    "base",
    "eth",
    "bsc",
    "arbitrum",
    "polygon_pos",
    "avax",
    "optimism",
    "blast",
)


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{GT_BASE}{path}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            url,
            params=params or {},
            headers={"Accept": "application/json", "User-Agent": UA},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"GeckoTerminal HTTP {resp.status_code}")
        ctype = (resp.headers.get("content-type") or "").lower()
        if "json" not in ctype:
            raise RuntimeError("GeckoTerminal non-JSON (challenge/block)")
        return resp.json()


async def fetch_new_pools(networks: list[str] | None = None, per_network: int = 12) -> list[dict]:
    nets = networks or list(_DEFAULT_NETWORKS)
    out: list[dict] = []
    for net in nets[:8]:
        try:
            data = await _get(f"/networks/{quote(net)}/new_pools", {"page": 1})
            rows = data.get("data") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                continue
            for row in rows[:per_network]:
                if isinstance(row, dict):
                    out.append({"_network": net, **row})
        except Exception as exc:
            logger.debug("GeckoTerminal new_pools %s: %s", net, exc)
    return out


def normalize_gecko_pool(row: dict) -> dict[str, Any] | None:
    attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
    net = str(row.get("_network") or "").strip().lower()
    chain = _NETWORK_CHAIN.get(net, net.replace("_", "") or "unknown")
    # base token address often in relationships or name like ADDRESS
    mint = ""
    rel = row.get("relationships") if isinstance(row.get("relationships"), dict) else {}
    base_rel = rel.get("base_token") if isinstance(rel.get("base_token"), dict) else {}
    base_data = base_rel.get("data") if isinstance(base_rel.get("data"), dict) else {}
    base_id = str(base_data.get("id") or "")
    # id format: {network}_{address}
    if "_" in base_id:
        mint = base_id.split("_", 1)[1]
    if not mint:
        mint = str(attrs.get("address") or attrs.get("base_token_address") or "").strip()
    if not mint:
        return None
    name = str(attrs.get("name") or "").strip()
    # name often "TOKEN / SOL"
    symbol = name.split("/")[0].strip()[:32] if name else "?"
    mc = _float(attrs.get("fdv_usd") or attrs.get("market_cap_usd") or attrs.get("reserve_in_usd"))
    liq = _float(attrs.get("reserve_in_usd") or attrs.get("liquidity_usd"))
    created = attrs.get("pool_created_at") or attrs.get("created_at")
    created_ms = _iso_to_ms(created)
    dex_id = str(attrs.get("dex_id") or attrs.get("dex") or "gecko").strip().lower()
    url = str(attrs.get("url") or f"https://www.geckoterminal.com/{net}/pools/{attrs.get('address') or ''}").strip()
    return {
        "candidate_id": f"{chain}:{mint}".lower(),
        "mint": mint,
        "symbol": symbol or "?",
        "name": name[:80],
        "chain": chain,
        "dex_id": dex_id or "gecko",
        "pair_address": str(attrs.get("address") or "").strip(),
        "market_cap": mc,
        "liq_usd": liq,
        "pair_created_ms": created_ms,
        "url": url,
        "price_usd": _float(attrs.get("base_token_price_usd")),
        "source": "gecko",
        "tags": ["gecko"],
        "raw": {"network": net, "gecko": True},
    }


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _iso_to_ms(ts: Any) -> int | None:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        val = int(ts)
        return val if val > 10_000_000_000 else val * 1000
    s = str(ts).strip()
    if not s:
        return None
    try:
        from datetime import datetime

        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None
