"""Pump.fun top-30 trader aggregation — public trades (+ optional Solana Tracker)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

import httpx

from app.config import settings
from app.launch_scout.client_pumpfun import fetch_recent_coins

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 18.0
UA = "CyclicalTrader-LaunchScout/1.0"
PUMP_V3 = "https://frontend-api-v3.pump.fun"
PUMP_SWAP = "https://swap-api.pump.fun"
ST_BASE = "https://data.solanatracker.io"


async def fetch_top_traders_and_events(
    *,
    top_n: int = 30,
    events_limit: int = 40,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    """
    Returns (traders, events, buy_mints).
    Prefer Solana Tracker PnL leaderboard when API key set; else aggregate Pump trades.
    """
    key = str(getattr(settings, "solana_tracker_api_key", "") or "").strip()
    if key:
        try:
            traders, events, mints = await _from_solana_tracker(key, top_n=top_n, events_limit=events_limit)
            if traders:
                return traders, events, mints
        except Exception as exc:
            logger.debug("Solana Tracker traders failed: %s", exc)
    return await _from_pump_public(top_n=top_n, events_limit=events_limit)


async def _from_solana_tracker(
    api_key: str, *, top_n: int, events_limit: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    headers = {"Accept": "application/json", "User-Agent": UA, "x-api-key": api_key}
    traders: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{ST_BASE}/v2/pnl/leaderboard", headers=headers, params={"limit": top_n})
        if resp.status_code >= 400:
            raise RuntimeError(f"ST leaderboard HTTP {resp.status_code}")
        data = resp.json()
        rows = data if isinstance(data, list) else data.get("data") or data.get("leaderboard") or []
        if not isinstance(rows, list):
            rows = []
        for i, row in enumerate(rows[:top_n]):
            if not isinstance(row, dict):
                continue
            wallet = str(row.get("wallet") or row.get("address") or row.get("owner") or "").strip()
            if not wallet:
                continue
            traders.append(
                {
                    "wallet": wallet,
                    "rank": i + 1,
                    "score": float(row.get("pnl") or row.get("realized") or row.get("volume") or 0),
                    "buys": int(row.get("buys") or row.get("trades") or 0),
                    "source": "solana_tracker",
                    "raw": row,
                }
            )
    # Without per-wallet recent trades from ST free tier, events stay empty; mints empty.
    return traders, [], set()


async def _from_pump_public(
    *, top_n: int, events_limit: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    coins = await fetch_recent_coins(limit=24)
    wallet_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"buys": 0, "volume": 0.0, "mints": set(), "events": []}
    )
    headers = {"Accept": "application/json", "User-Agent": UA}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for coin in coins[:14]:
            mint = str(coin.get("mint") or coin.get("coinMint") or coin.get("address") or "").strip()
            if not mint:
                continue
            symbol = str(coin.get("symbol") or coin.get("ticker") or "?").strip()[:32]
            # Also score serial creators (dev wallets) as early-signal wallets
            creator = str(coin.get("creator") or coin.get("dev") or "").strip()
            if creator and len(creator) >= 20:
                st = wallet_stats[creator]
                st["buys"] += 1
                st["mints"].add(mint.lower())
            try:
                r = await client.get(
                    f"{PUMP_SWAP}/v2/coins/{mint}/trades",
                    headers=headers,
                    params={"limit": 40},
                )
                if r.status_code >= 400:
                    logger.debug("Pump swap trades %s → %s", mint[:8], r.status_code)
                    continue
                _ingest_trades(
                    wallet_stats,
                    _as_trade_rows(r.json()),
                    prefer_buy=True,
                    mint=mint,
                    symbol=symbol,
                )
            except Exception as exc:
                logger.debug("Pump trades %s: %s", mint[:8], exc)

    ranked = sorted(
        wallet_stats.items(),
        key=lambda kv: (kv[1]["buys"], kv[1]["volume"]),
        reverse=True,
    )[:top_n]
    traders: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    buy_mints: set[str] = set()
    now = int(time.time())
    for i, (wallet, st) in enumerate(ranked):
        traders.append(
            {
                "wallet": wallet,
                "rank": i + 1,
                "score": float(st["volume"]),
                "buys": int(st["buys"]),
                "source": "pump_public",
                "raw": {"mints": list(st["mints"])[:12]},
            }
        )
        for ev in st["events"][:3]:
            events.append(ev)
            if ev.get("mint"):
                buy_mints.add(str(ev["mint"]).lower())
    events.sort(key=lambda e: int(e.get("ts_unix") or 0), reverse=True)
    events = events[:events_limit]
    # Ensure timestamps
    for e in events:
        e.setdefault("ts_unix", now)
    return traders, events, buy_mints


def _as_trade_rows(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("trades", "data", "results", "items"):
            v = data.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def _ingest_trades(
    wallet_stats: dict[str, dict[str, Any]],
    trades: list[dict],
    *,
    prefer_buy: bool,
    mint: str = "",
    symbol: str = "?",
) -> None:
    for t in trades:
        is_buy = t.get("is_buy")
        if is_buy is None:
            side = str(t.get("side") or t.get("type") or "").lower()
            is_buy = side in ("buy", "b", "1", "true")
        if prefer_buy and not is_buy:
            continue
        wallet = str(
            t.get("userAddress")
            or t.get("user")
            or t.get("trader")
            or t.get("owner")
            or t.get("wallet")
            or t.get("maker")
            or ""
        ).strip()
        if not wallet or len(wallet) < 20:
            continue
        mint_u = str(t.get("mint") or t.get("coinMint") or mint or "").strip()
        sym = str(t.get("symbol") or symbol or "?").strip()[:32]
        try:
            sol_amt = float(
                t.get("amountSol")
                or t.get("sol_amount")
                or t.get("solAmount")
                or t.get("amount_sol")
                or 0
            )
        except (TypeError, ValueError):
            sol_amt = 0.0
        try:
            usd = float(
                t.get("amountUsd") or t.get("usd_amount") or t.get("usdAmount") or 0
            )
        except (TypeError, ValueError):
            usd = 0.0
        vol = usd if usd > 0 else sol_amt * 150.0  # rough SOL→USD for ranking only
        ts = t.get("timestamp") or t.get("created_timestamp") or t.get("block_time")
        ts_i = _trade_ts(ts)
        st = wallet_stats[wallet]
        st["buys"] += 1
        st["volume"] += vol
        if mint_u:
            st["mints"].add(mint_u.lower())
        st["events"].append(
            {
                "event_id": f"pump-{wallet[:8]}-{mint_u[:12]}-{ts_i}",
                "wallet": wallet,
                "action": "buy",
                "mint": mint_u,
                "symbol": sym,
                "chain": "solana",
                "usd_amount": usd or vol,
                "ts_unix": ts_i,
                "source": "pump",
            }
        )


def _trade_ts(ts: Any) -> int:
    if ts is None:
        return int(time.time())
    if isinstance(ts, (int, float)):
        val = int(ts)
        return val // 1000 if val > 10_000_000_000 else val
    s = str(ts).strip()
    if not s:
        return int(time.time())
    try:
        from datetime import datetime

        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return int(time.time())


def aggregate_normalize_demo(trades: list[dict]) -> list[dict[str, Any]]:
    """Pure helper for unit tests — rank wallets by buy count."""
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"buys": 0, "volume": 0.0, "mints": set(), "events": []})
    _ingest_trades(stats, trades, prefer_buy=True, mint="MintDemo", symbol="DEMO")
    ranked = sorted(stats.items(), key=lambda kv: (kv[1]["buys"], kv[1]["volume"]), reverse=True)
    return [
        {"wallet": w, "rank": i + 1, "buys": st["buys"], "score": st["volume"], "source": "pump_public"}
        for i, (w, st) in enumerate(ranked)
    ]
