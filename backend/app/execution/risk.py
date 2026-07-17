"""Risk checks and cooldowns for execution agent."""

from __future__ import annotations

from app.config import settings
from app.execution import db as exec_db
from app.execution.models import SignalCandidate
from app.paper import paper_db


async def check_risk(
    candidate: SignalCandidate,
    *,
    enabled: bool,
    max_daily: int | None = None,
    cooldown_hours: int | None = None,
) -> tuple[bool, str]:
    if not enabled:
        return False, "execution_disabled"

    max_d = max_daily if max_daily is not None else settings.execution_max_daily
    cooldown = cooldown_hours if cooldown_hours is not None else settings.execution_cooldown_hours

    today_count = await exec_db.count_proposals_today()
    if today_count >= max_d:
        return False, "daily_limit_reached"

    recent = await exec_db.recent_symbol_proposal(candidate.symbol, cooldown)
    if recent and recent.get("status") in ("executed", "dry_run", "pending", "approved"):
        return False, "symbol_cooldown"

    position = await paper_db.get_position(candidate.symbol)
    if position and float(position.get("quantity") or 0) > 0:
        return False, "paper_position_exists"

    return True, "ok"
