"""Paper portfolio cleanup — remove positions opened by execution agent mirror."""

from __future__ import annotations

import logging

from app.execution import db as exec_db
from app.paper.executor import close_position, place_order
from app.paper import paper_db
from app.paper.pricing import PaperTradeError

logger = logging.getLogger(__name__)

_AGENT_STATUSES = frozenset({"dry_run", "executed", "approved"})


async def _proposal_symbols() -> set[str]:
    proposals = await exec_db.list_proposals(limit=500)
    return {p["symbol"] for p in proposals if p.get("status") in _AGENT_STATUSES}


async def purge_execution_agent_positions(*, force: bool = False) -> dict:
    """Close open positions tied to execution agent proposals or agent-only trades."""
    proposal_symbols = await _proposal_symbols()
    execution_only = set(
        await paper_db.list_symbols_for_trade_source("execution_agent", only_source=True)
    )
    targets = sorted(proposal_symbols | execution_only)

    purged: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []

    positions = await paper_db.get_positions()
    by_symbol = {str(p["symbol"]): p for p in positions}

    for sym in targets:
        position = by_symbol.get(sym)
        if not position:
            continue
        qty = float(position.get("quantity") or 0.0)
        if abs(qty) < 1e-9:
            continue

        if not force and sym not in proposal_symbols:
            trades = await paper_db.get_trades_for_symbol(sym, limit=100)
            has_user = any(t.get("trade_source") == "user" for t in trades)
            has_agent = any(t.get("trade_source") == "execution_agent" for t in trades)
            if has_user and not has_agent:
                skipped.append({"symbol": sym, "reason": "user_trades"})
                continue

        try:
            await close_position(sym, percent=100.0)
            purged.append(sym)
            logger.info("Purged execution-agent position: %s", sym)
            continue
        except PaperTradeError as exc:
            logger.warning("Close failed in purge for %s: %s", sym, exc)

        try:
            await place_order(
                symbol=sym,
                side="sell" if qty > 0 else "buy",
                quantity=abs(qty),
                price_native_override=float(position["avg_price_native"]),
                trade_source="system_purge",
            )
            purged.append(sym)
        except PaperTradeError as exc:
            failed.append({"symbol": sym, "error": exc.message, "code": exc.code})

    return {
        "status": "ok",
        "purged": purged,
        "skipped": skipped,
        "failed": failed,
        "proposal_symbols": sorted(proposal_symbols),
    }
