"""HTTP client for Cope Capital (api.cope.capital) — Fomo smart-money graph."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

COPE_BASE = "https://api.cope.capital/v1"
HTTP_TIMEOUT = 25.0


def resolve_cope_api_key() -> str:
    """Prefer CYCLICAL_COPE_API_KEY; fall back to COPE_API_KEY."""
    key = (getattr(settings, "cope_api_key", None) or "").strip()
    if key:
        return key
    return (os.environ.get("COPE_API_KEY") or "").strip()


class CopeClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (api_key or resolve_cope_api_key()).strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "CyclicalTrader-FomoGhost/1.0",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.api_key:
            raise RuntimeError("COPE_API_KEY missing")
        url = f"{COPE_BASE}{path}"
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url, headers=self._headers(), params=params or {})
            if resp.status_code == 402:
                raise RuntimeError("Cope activity quota exhausted (402) — wait for UTC midnight or enable x402")
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{COPE_BASE}{path}"
        headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "CyclicalTrader-FomoGhost/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=body or {})
            if resp.status_code >= 400:
                snippet = (resp.text or "")[:200].replace("\n", " ")
                raise RuntimeError(f"Cope POST {path} HTTP {resp.status_code}: {snippet}")
            try:
                return resp.json()
            except Exception as exc:
                snippet = (resp.text or "")[:200].replace("\n", " ")
                raise RuntimeError(f"Cope POST {path} non-JSON response: {snippet}") from exc

    async def register(self, agent_name: str = "cyclical-trader-fomo-ghost", description: str = "") -> dict:
        """POST /v1/register — no auth required; returns api_key."""
        data = await self._post(
            "/register",
            {"agent_name": agent_name, "description": description or "Cyclical Trader FOMO Ghost top-30"},
        )
        if isinstance(data, dict) and data.get("api_key"):
            self.api_key = str(data["api_key"])
        return data if isinstance(data, dict) else {"raw": data}

    async def leaderboard(self, timeframe: str = "7d", limit: int = 30) -> list[dict]:
        data = await self._get("/leaderboard", {"timeframe": timeframe, "limit": limit})
        return _as_list(data, keys=("traders", "leaderboard", "data", "results"))

    async def activity_poll(self, since: int | None = None) -> dict:
        params: dict[str, Any] = {}
        if since is not None:
            params["since"] = since
        data = await self._get("/activity/poll", params)
        return data if isinstance(data, dict) else {"count": 0, "latest_at": since}

    async def activity(self, since: int | None = None, action: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if since is not None:
            params["since"] = since
        if action:
            params["action"] = action
        data = await self._get("/activity", params)
        return _as_list(data, keys=("activity", "trades", "data", "results", "items"))

    async def account_usage(self) -> dict:
        try:
            data = await self._get("/account/usage")
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.debug("Cope usage fetch failed: %s", exc)
            return {}


def _as_list(data: Any, keys: tuple[str, ...]) -> list[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        # single trader object wrapping
        if "handle" in data:
            return [data]
    return []


def normalize_trader(row: dict, rank: int) -> dict:
    handle = str(row.get("handle") or row.get("username") or row.get("name") or "").lstrip("@").strip()
    pnl = _num(row.get("pnl") if row.get("pnl") is not None else row.get("pnl_usd"))
    win_rate = _num(row.get("win_rate") if row.get("win_rate") is not None else row.get("winrate"))
    trades = int(row.get("trades") or row.get("trade_count") or row.get("n_trades") or 0)
    return {
        "rank": int(row.get("rank") or rank),
        "handle": handle,
        "pnl": pnl,
        "win_rate": win_rate,
        "trades": trades,
        "raw": row,
    }


def normalize_activity(row: dict) -> dict | None:
    handle = str(
        row.get("handle")
        or row.get("fomo_handle")
        or row.get("trader")
        or row.get("username")
        or ""
    ).lstrip("@").strip()
    action = str(row.get("action") or row.get("side") or "").lower().strip()
    if action in ("buy", "long", "accumulate"):
        action = "buy"
    elif action in ("sell", "short", "exit"):
        action = "sell"
    else:
        return None
    mint = str(row.get("mint") or row.get("token_mint") or row.get("token_address") or row.get("address") or "").strip()
    symbol = str(row.get("symbol") or row.get("token_symbol") or row.get("ticker") or "?").strip()
    chain = str(row.get("chain") or row.get("network") or "solana").lower().strip()
    usd = _num(row.get("usd_amount") if row.get("usd_amount") is not None else row.get("usd") or row.get("amount_usd"))
    ts = row.get("timestamp") or row.get("ts") or row.get("at") or row.get("created_at") or row.get("time")
    ts_unix = _to_unix(ts)
    event_id = str(
        row.get("id")
        or row.get("tx")
        or row.get("tx_hash")
        or row.get("signature")
        or f"{handle}:{mint}:{action}:{ts_unix}"
    )
    if not handle or not mint:
        return None
    return {
        "event_id": event_id,
        "handle": handle,
        "action": action,
        "mint": mint,
        "symbol": symbol[:32],
        "chain": chain[:24],
        "usd_amount": usd,
        "ts_unix": ts_unix,
        "raw": row,
    }


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_unix(ts: Any) -> int:
    if ts is None:
        return 0
    if isinstance(ts, (int, float)):
        val = int(ts)
        # ms → s
        return val // 1000 if val > 10_000_000_000 else val
    if isinstance(ts, str):
        s = ts.strip()
        if s.isdigit():
            return _to_unix(int(s))
        try:
            from datetime import datetime

            return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return 0
    return 0
