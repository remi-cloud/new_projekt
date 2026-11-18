"""Pump.fun feeder — ultra-early Solana bonding / fresh mints (best-effort)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 18.0
UA = "CyclicalTrader-LaunchScout/1.0"

_ENDPOINTS = (
    "https://frontend-api-v3.pump.fun/coins?offset=0&limit={limit}&sort=created_timestamp&order=DESC&includeNsfw=false",
    "https://advanced-api-v2.pump.fun/coins/list?limit={limit}&sortBy=creationTime&direction=desc",
)

_status = {
    "id": "pump.fun",
    "http": None,
    "detail": "Jeszcze nie sprawdzono. Pusta kolumna oznacza brak odpowiedzi źródła.",
}


def source_status() -> dict:
    return dict(_status)


def _remember(http: int | None, detail: str) -> None:
    _status["http"] = http
    _status["detail"] = detail


async def fetch_recent_coins(limit: int = 60) -> list[dict]:
    limit = max(1, min(100, limit))
    saw_forbidden = False
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=False) as client:
        for tmpl in _ENDPOINTS:
            url = tmpl.format(limit=limit)
            try:
                resp = await client.get(url, headers={"Accept": "application/json", "User-Agent": UA})
                if resp.status_code in {401, 403}:
                    saw_forbidden = True
                    logger.info("pump.fun odmówił HTTP %s — bez obchodzenia blokady", resp.status_code)
                    continue
                if resp.status_code >= 400:
                    logger.info("pump.fun HTTP %s — kolumna zostaje pusta", resp.status_code)
                    continue
                data = resp.json()
                rows = _as_rows(data)
                if rows:
                    _remember(200, "Źródło odpowiedziało.")
                    return rows[:limit]
            except Exception as exc:
                logger.info("pump.fun nie odpowiedziało (%s)", type(exc).__name__)
    if saw_forbidden:
        _remember(403, "pump.fun zwróciło 403. Brak danych, bez obejść i bez scrapowania.")
    else:
        _remember(None, "pump.fun nie odpowiedziało. Pusta kolumna oznacza brak danych źródła.")
    return []


def _as_rows(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("coins", "data", "results", "items"):
            v = data.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def normalize_pump_coin(row: dict) -> dict[str, Any] | None:
    mint = str(row.get("mint") or row.get("coinMint") or row.get("address") or "").strip()
    if not mint:
        return None
    symbol = str(row.get("symbol") or row.get("ticker") or "?").strip()[:32]
    name = str(row.get("name") or "").strip()[:80]
    mc = row.get("usd_market_cap")
    if mc is None:
        mc = row.get("market_cap") or row.get("usdMarketCap") or row.get("marketCap")
    try:
        mc_f = float(mc) if mc is not None else None
    except (TypeError, ValueError):
        mc_f = None
    # Bonding progress sometimes exposed as virtual SOL / market cap only
    created = row.get("created_timestamp") or row.get("createdAt") or row.get("creationTime")
    try:
        if created is None:
            created_ms = None
        else:
            created_i = int(created)
            created_ms = created_i if created_i > 10_000_000_000 else created_i * 1000
    except (TypeError, ValueError):
        created_ms = None
    complete = bool(row.get("complete") or row.get("is_complete") or row.get("graduated"))
    tags = ["pump"]
    if not complete:
        tags.append("planned_visibility")
        tags.append("bonding")
    else:
        tags.append("migrated")
    return {
        "candidate_id": f"solana:{mint}".lower(),
        "mint": mint,
        "symbol": symbol,
        "name": name,
        "chain": "solana",
        "dex_id": "pumpfun" if not complete else "pumpswap",
        "pair_address": "",
        "market_cap": mc_f,
        "liq_usd": _float(row.get("liquidity") or row.get("liquidity_usd")),
        "pair_created_ms": created_ms,
        "url": f"https://pump.fun/{mint}",
        "price_usd": _float(row.get("price_usd") or row.get("usd_price")),
        "source": "pump",
        "tags": tags,
        "raw": {"complete": complete, "pump": True},
    }


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
