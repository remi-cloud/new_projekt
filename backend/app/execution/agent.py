"""Execution agent orchestrator."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings
from app.execution import db as exec_db
from app.execution.brokers import get_broker_adapter
from app.execution.models import BrokerOrderRequest, ExecutionRunResult, SignalCandidate
from app.execution.risk import check_risk
from app.execution.router import route_broker
from app.execution.signals import collect_signal_candidates
from app.execution.sizing import compute_amount_pln
from app.paper.executor import place_order
from app.paper.pricing import PaperTradeError
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

_last_run_at: str | None = None


def get_last_run_at() -> str | None:
    return _last_run_at


async def get_effective_settings() -> dict:
    runtime = await exec_db.get_runtime_settings()
    out = {
        "enabled": bool(runtime["enabled"]) if runtime and runtime.get("enabled") is not None else settings.execution_enabled,
        "dry_run": bool(runtime["dry_run"]) if runtime and runtime.get("dry_run") is not None else settings.execution_dry_run,
        "mirror_paper": bool(runtime["mirror_paper"]) if runtime and runtime.get("mirror_paper") is not None else settings.execution_mirror_paper,
        "require_approval": bool(runtime["require_approval"]) if runtime and runtime.get("require_approval") is not None else settings.execution_require_approval,
        "min_confidence": float(runtime["min_confidence"]) if runtime and runtime.get("min_confidence") is not None else settings.execution_min_confidence,
        "amount_pln": float(runtime["amount_pln"]) if runtime and runtime.get("amount_pln") is not None else settings.execution_amount_pln,
        "max_daily": int(runtime["max_daily"]) if runtime and runtime.get("max_daily") is not None else settings.execution_max_daily,
        "cooldown_hours": int(runtime["cooldown_hours"]) if runtime and runtime.get("cooldown_hours") is not None else settings.execution_cooldown_hours,
    }
    if out["dry_run"]:
        out["mirror_paper"] = False
    return out


async def run_once(*, force: bool = False) -> ExecutionRunResult:
    global _last_run_at

    eff = await get_effective_settings()
    if not eff["enabled"] and not force:
        return ExecutionRunResult(processed=0, created=0, executed=0, skipped=0, errors=0)

    if scanner.scan_in_progress and not force:
        logger.debug("Execution tick skipped — scan in progress")
        return ExecutionRunResult(processed=0, created=0, executed=0, skipped=0, errors=0)

    candidates = await collect_signal_candidates(eff["min_confidence"])
    created = executed = skipped = errors = 0

    for candidate in candidates:
        ok, reason = await check_risk(
            candidate,
            enabled=eff["enabled"] or force,
            max_daily=eff["max_daily"],
            cooldown_hours=eff["cooldown_hours"],
        )
        if not ok:
            skipped += 1
            continue

        primary, fallback = route_broker(candidate)
        broker_id = await _resolve_broker(primary, fallback)
        if not broker_id:
            await _save_skipped(candidate, primary or "unknown", "skipped_no_credentials", eff)
            skipped += 1
            continue

        amount_pln = compute_amount_pln(
            eff["amount_pln"],
            confidence=candidate.confidence,
        )
        if amount_pln <= 0:
            skipped += 1
            continue
        status = "pending" if eff["require_approval"] else ("dry_run" if eff["dry_run"] else "pending")

        proposal_id = await exec_db.insert_proposal({
            "symbol": candidate.symbol,
            "name": candidate.name,
            "asset_class": candidate.asset_class,
            "region": candidate.region,
            "broker_id": broker_id,
            "source": candidate.source,
            "confidence": candidate.confidence,
            "amount_pln": amount_pln,
            "rationale": candidate.rationale,
            "status": status,
        })
        created += 1

        if eff["require_approval"]:
            continue

        success = await execute_proposal(proposal_id, eff)
        if success:
            executed += 1
        else:
            errors += 1

    _last_run_at = datetime.now(timezone.utc).isoformat()
    await exec_db.record_agent_run(len(candidates), created)
    return ExecutionRunResult(
        processed=len(candidates),
        created=created,
        executed=executed,
        skipped=skipped,
        errors=errors,
    )


async def _resolve_broker(primary: str, fallback: str | None) -> str | None:
    for bid in (primary, fallback):
        if not bid:
            continue
        try:
            adapter = get_broker_adapter(bid)
        except KeyError:
            continue
        if await adapter.is_configured() or settings.execution_dry_run:
            return bid
    return primary if settings.execution_dry_run else None


async def _save_skipped(
    candidate: SignalCandidate,
    broker_id: str,
    status: str,
    eff: dict,
) -> None:
    await exec_db.insert_proposal({
        "symbol": candidate.symbol,
        "name": candidate.name,
        "asset_class": candidate.asset_class,
        "region": candidate.region,
        "broker_id": broker_id,
        "source": candidate.source,
        "confidence": candidate.confidence,
        "amount_pln": compute_amount_pln(
            eff["amount_pln"],
            confidence=candidate.confidence,
        ),
        "rationale": candidate.rationale,
        "status": status,
        "error_message": status,
    })


async def execute_proposal(proposal_id: int, eff: dict | None = None) -> bool:
    eff = eff or await get_effective_settings()
    row = await exec_db.get_proposal(proposal_id)
    if not row:
        return False

    broker_id = row["broker_id"]
    try:
        adapter = get_broker_adapter(broker_id)
    except KeyError:
        await exec_db.update_proposal(proposal_id, status="failed", error_message="unknown_broker")
        return False

    dry_run = eff["dry_run"]
    req = BrokerOrderRequest(
        symbol=row["symbol"],
        side="buy",
        amount_pln=float(row["amount_pln"]),
        asset_class=row["asset_class"],
    )

    if not dry_run and not await adapter.is_configured():
        await exec_db.update_proposal(
            proposal_id,
            status="skipped_no_credentials",
            error_message="broker_not_configured",
        )
        return False

    result = await adapter.place_market_order(req, dry_run=dry_run)
    now = datetime.now(timezone.utc).isoformat()
    paper_trade_id = None

    if not result.success and not dry_run:
        await exec_db.update_proposal(
            proposal_id,
            status="failed",
            error_message=result.message,
        )
        return False

    # Mirror to paper only after a successful live broker execution.
    should_mirror = bool(eff["mirror_paper"]) and not dry_run and bool(result.success)
    if should_mirror:
        try:
            await place_order(
                symbol=row["symbol"],
                side="buy",
                amount_pln=float(row["amount_pln"]),
                trade_source="execution_agent",
            )
        except PaperTradeError as exc:
            logger.warning("Paper mirror failed for %s: %s", row["symbol"], exc)

    final_status = "dry_run" if dry_run or result.dry_run else "executed"
    await exec_db.update_proposal(
        proposal_id,
        status=final_status,
        broker_order_id=result.order_id,
        paper_trade_id=paper_trade_id,
        executed_at=now,
        error_message=None if result.success else result.message,
    )
    return True


async def approve_proposal(proposal_id: int) -> bool:
    row = await exec_db.get_proposal(proposal_id)
    if not row or row.get("status") != "pending":
        return False
    await exec_db.update_proposal(proposal_id, status="approved")
    return await execute_proposal(proposal_id)
