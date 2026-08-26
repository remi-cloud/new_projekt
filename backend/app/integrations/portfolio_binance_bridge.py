"""Portfolio ↔ Binance Trade bridge — paper book vs spot balances."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.data.whale_flows import BINANCE_SYMBOLS
from app.execution.brokers.binance import BinanceAdapter
from app.integrations.binance_spot import binance_configured, binance_trade_url
from app.paper.portfolio_service import build_portfolio

_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}
_CACHE_TTL = 120.0


def _catalog_symbol(binance_pair: str) -> str | None:
    for sym, pair in BINANCE_SYMBOLS.items():
        if pair == binance_pair:
            return sym
    asset = binance_pair.replace("USDT", "")
    if asset:
        return f"{asset}-USD"
    return None


async def build_binance_sync(*, force: bool = False) -> dict[str, Any]:
    now_mono = time.monotonic()
    if not force and _CACHE["payload"] and now_mono - float(_CACHE["at"]) < _CACHE_TTL:
        return _CACHE["payload"]

    now_iso = datetime.now(timezone.utc).isoformat()
    connected = binance_configured()
    dry_run = bool(getattr(settings, "binance_ai_bot_dry_run", True))

    paper = await build_portfolio()
    paper_positions: list[dict[str, Any]] = []
    for pos in paper.get("positions") or []:
        sym = str(pos.get("symbol") or "")
        if sym not in BINANCE_SYMBOLS:
            continue
        paper_positions.append(
            {
                "symbol": sym,
                "quantity": float(pos.get("quantity") or 0),
                "market_value_pln": pos.get("market_value_pln"),
                "asset_class": pos.get("asset_class"),
            }
        )

    binance_positions: list[dict[str, Any]] = []
    trade_links: dict[str, str] = {}
    adapter = BinanceAdapter()

    if connected:
        for bp in await adapter.get_open_positions():
            pair = BINANCE_SYMBOLS.get(bp.symbol, f"{bp.symbol.replace('-USD', '')}USDT")
            trade_links[bp.symbol] = binance_trade_url(pair)
            binance_positions.append(
                {
                    "symbol": bp.symbol,
                    "quantity": bp.quantity,
                    "binance_pair": pair,
                    "trade_url": trade_links[bp.symbol],
                }
            )

    paper_by_sym = {p["symbol"]: p for p in paper_positions}
    binance_by_sym = {p["symbol"]: p for p in binance_positions}
    drift: list[dict[str, Any]] = []
    alert_pct = float(getattr(settings, "binance_drift_alert_pct", 15) or 15)

    for sym in sorted(set(paper_by_sym) | set(binance_by_sym)):
        pq = float((paper_by_sym.get(sym) or {}).get("quantity") or 0)
        bq = float((binance_by_sym.get(sym) or {}).get("quantity") or 0)
        if pq == 0 and bq == 0:
            continue
        base = max(abs(pq), abs(bq), 1e-12)
        delta_pct = ((bq - pq) / base) * 100.0
        if abs(delta_pct) < 0.01 and pq == bq:
            continue
        drift.append(
            {
                "symbol": sym,
                "paper_qty": pq,
                "binance_qty": bq,
                "delta_pct": round(delta_pct, 2),
                "alert": abs(delta_pct) >= alert_pct,
                "trade_url": trade_links.get(sym) or binance_trade_url(BINANCE_SYMBOLS.get(sym, "")),
            }
        )

    payload = {
        "ok": True,
        "connected": connected,
        "configured": connected,
        "dry_run": dry_run,
        "last_sync_at": now_iso,
        "paper_positions": paper_positions,
        "binance_positions": binance_positions,
        "drift": drift,
        "drift_count": len(drift),
        "drift_alerts": sum(1 for d in drift if d.get("alert")),
        "trade_links": trade_links,
        "catalog_symbols": list(BINANCE_SYMBOLS.keys()),
    }

    _CACHE["at"] = now_mono
    _CACHE["payload"] = payload
    return payload
