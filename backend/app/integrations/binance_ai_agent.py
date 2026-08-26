"""Binance AI BOT — reconcile portfolio drift + signal proposals (dry-run default)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.execution import db as exec_db
from app.execution.agent import get_effective_settings
from app.execution.models import SignalCandidate
from app.execution.signals import collect_signal_candidates
from app.execution.sizing import compute_amount_pln
from app.integrations.portfolio_binance_bridge import build_binance_sync
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)

_last_tick_at: str | None = None
_last_result: dict[str, Any] | None = None


def _enabled() -> bool:
    return bool(getattr(settings, "binance_ai_bot_enabled", True))


async def run_binance_ai_tick(*, force: bool = False) -> dict[str, Any]:
    global _last_tick_at, _last_result

    now_iso = datetime.now(timezone.utc).isoformat()
    if not _enabled() and not force:
        return {"ok": False, "reason": "disabled", "at": now_iso}

    await exec_db.init_execution_db()
    sync = await build_binance_sync(force=force)
    eff = await get_effective_settings()
    min_conf = float(eff.get("min_confidence") or 70)
    dry_run = bool(getattr(settings, "binance_ai_bot_dry_run", True)) or eff.get("dry_run", True)

    proposals_created = 0
    drift_alerts = sync.get("drift_alerts") or 0
    notes: list[str] = []

    if drift_alerts:
        notes.append(f"drift_alerts={drift_alerts}")

    binance_syms = {p["symbol"] for p in sync.get("binance_positions") or []}
    candidates = await collect_signal_candidates(min_conf)
    crypto_candidates = [c for c in candidates if c.asset_class == "crypto" or c.symbol in sync.get("catalog_symbols", [])]

    for candidate in crypto_candidates[:5]:
        if candidate.symbol in binance_syms:
            continue
        if candidate.symbol not in (sync.get("catalog_symbols") or []):
            continue
        created = await _maybe_propose(candidate, eff, dry_run)
        if created:
            proposals_created += 1

    result = {
        "ok": True,
        "at": now_iso,
        "connected": sync.get("connected"),
        "dry_run": dry_run,
        "drift_count": sync.get("drift_count"),
        "drift_alerts": drift_alerts,
        "proposals_created": proposals_created,
        "signal_candidates": len(crypto_candidates),
        "notes": notes,
    }

    _last_tick_at = now_iso
    _last_result = result

    try:
        await broadcaster.publish("binance_bot_tick", result)
    except Exception as exc:
        logger.debug("binance_bot_tick publish failed: %s", exc)

    logger.info(
        "Binance AI BOT: connected=%s drift=%s proposals=%d dry_run=%s",
        sync.get("connected"),
        sync.get("drift_count"),
        proposals_created,
        dry_run,
    )
    return result


async def _maybe_propose(candidate: SignalCandidate, eff: dict, dry_run: bool) -> bool:
    pending = await exec_db.pending_broker_proposal(candidate.symbol, "binance")
    if pending:
        return False

    cooldown = int(eff.get("cooldown_hours") or 24)
    recent = await exec_db.recent_symbol_proposal(candidate.symbol, cooldown)
    if recent and recent.get("broker_id") == "binance" and recent.get("status") in (
        "executed",
        "dry_run",
        "pending",
        "approved",
    ):
        return False

    amount_pln = compute_amount_pln(
        float(eff.get("amount_pln") or 10000),
        confidence=candidate.confidence,
    )
    if amount_pln <= 0:
        return False
    status = "pending" if eff.get("require_approval") else ("dry_run" if dry_run else "pending")
    await exec_db.insert_proposal(
        {
            "symbol": candidate.symbol,
            "name": candidate.name,
            "asset_class": candidate.asset_class,
            "region": candidate.region,
            "broker_id": "binance",
            "source": candidate.source,
            "confidence": candidate.confidence,
            "amount_pln": amount_pln,
            "rationale": f"Binance AI BOT: {candidate.rationale[:200]}",
            "status": status,
        }
    )
    return True


def get_binance_bot_status() -> dict[str, Any]:
    return {
        "enabled": _enabled(),
        "last_tick_at": _last_tick_at,
        "last_result": _last_result,
        "dry_run": bool(getattr(settings, "binance_ai_bot_dry_run", True)),
        "interval_seconds": int(getattr(settings, "binance_ai_bot_interval_seconds", 120) or 120),
    }
