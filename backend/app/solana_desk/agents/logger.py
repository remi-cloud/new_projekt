"""The only writer of decision rows. Empty reasons are refused."""

from __future__ import annotations

from typing import Any

from app.solana_desk.learning.apply import effects_for
from app.solana_desk.learning.postmortem import queue
from app.solana_desk.store import insert_decision


async def write(
    *,
    kind: str,
    agent: str,
    reason: str,
    mint: str = "",
    symbol: str = "",
    size_pct: float | None = None,
    size_sol: float | None = None,
    size_usd: float | None = None,
    price: float | None = None,
    slip: float | None = None,
    pnl_sol: float | None = None,
    pnl_usd: float | None = None,
    fill_source: str | None = None,
    parent_id: int | None = None,
    detail: dict | None = None,
) -> dict[str, Any]:
    text = str(reason or "").strip()
    if not text:
        queue({"agent": "logger", "trigger": "empty_reason", "features": {"reason_len": 0}})
        raise ValueError("reason required")
    detail = dict(detail or {})
    effects = await effects_for("logger", {"reason_len": len(text)})
    needs_source = any(item.type == "require_check" and item.param == "reason_source" for item in effects)
    if needs_source and not str(detail.get("reason_source") or "").strip():
        raise ValueError("lesson requires reason_source")
    if effects and "lesson #" not in text:
        text = f"{text} · lesson #{effects[0].lesson_id}"
    return await insert_decision(
        kind=kind,
        agent=agent,
        reason=text,
        mint=mint,
        symbol=symbol,
        size_pct=size_pct,
        size_sol=size_sol,
        size_usd=size_usd,
        price=price,
        slip=slip,
        pnl_sol=pnl_sol,
        pnl_usd=pnl_usd,
        fill_source=fill_source,
        parent_id=parent_id,
        detail=detail,
    )
