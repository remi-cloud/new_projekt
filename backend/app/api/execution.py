"""API for broker execution agent."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.execution import db as exec_db
from app.execution.agent import approve_proposal, get_effective_settings, get_last_run_at, run_once
from app.execution.brokers import all_broker_adapters
from app.execution.models import BrokerStatus, ExecutionRunResult, ExecutionSettingsView, ExecutionStatus, TradeProposal
from app.config import settings

router = APIRouter(prefix="/api/execution", tags=["execution"])


class ExecutionSettingsPatch(BaseModel):
    enabled: bool | None = None
    dry_run: bool | None = None
    mirror_paper: bool | None = None
    require_approval: bool | None = None
    min_confidence: float | None = Field(default=None, ge=0, le=100)
    amount_pln: float | None = Field(default=None, gt=0)
    max_daily: int | None = Field(default=None, ge=1, le=50)
    cooldown_hours: int | None = Field(default=None, ge=1, le=168)


def _row_to_proposal(row: dict) -> TradeProposal:
    return TradeProposal(
        id=row["id"],
        symbol=row["symbol"],
        name=row["name"],
        asset_class=row["asset_class"],
        region=row.get("region") or "global",
        broker_id=row["broker_id"],
        source=row["source"],
        confidence=float(row["confidence"]),
        amount_pln=float(row["amount_pln"]),
        rationale=row.get("rationale") or "",
        status=row["status"],
        broker_order_id=row.get("broker_order_id"),
        paper_trade_id=row.get("paper_trade_id"),
        error_message=row.get("error_message"),
        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        executed_at=(
            datetime.fromisoformat(row["executed_at"].replace("Z", "+00:00"))
            if row.get("executed_at")
            else None
        ),
    )


async def _settings_view() -> ExecutionSettingsView:
    eff = await get_effective_settings()
    return ExecutionSettingsView(
        enabled=eff["enabled"],
        dry_run=eff["dry_run"],
        mirror_paper=eff["mirror_paper"],
        require_approval=eff["require_approval"],
        min_confidence=eff["min_confidence"],
        amount_pln=eff["amount_pln"],
        max_daily=eff["max_daily"],
        cooldown_hours=eff["cooldown_hours"],
        broker_crypto=settings.execution_broker_crypto,
        broker_equity=settings.execution_broker_equity,
        broker_equity_fallback=settings.execution_broker_equity_fallback,
    )


@router.get("/status", response_model=ExecutionStatus)
async def execution_status():
    eff = await get_effective_settings()
    last = await exec_db.get_last_run()
    brokers: list[BrokerStatus] = []
    for adapter in all_broker_adapters():
        brokers.append(
            BrokerStatus(
                broker_id=adapter.broker_id,
                name=adapter.name,
                configured=await adapter.is_configured(),
                connected=await adapter.is_connected(),
            )
        )
    return ExecutionStatus(
        enabled=eff["enabled"],
        dry_run=eff["dry_run"],
        mirror_paper=eff["mirror_paper"],
        require_approval=eff["require_approval"],
        proposals_today=await exec_db.count_proposals_today(),
        max_daily=eff["max_daily"],
        last_run_at=last.get("last_run_at") if last else get_last_run_at(),
        settings=await _settings_view(),
        brokers=brokers,
    )


@router.get("/proposals", response_model=list[TradeProposal])
async def execution_proposals(limit: int = 50, status: str | None = None):
    rows = await exec_db.list_proposals(limit=limit, status=status)
    return [_row_to_proposal(r) for r in rows]


@router.post("/proposals/{proposal_id}/approve")
async def execution_approve(proposal_id: int):
    ok = await approve_proposal(proposal_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Proposal not found or not pending")
    row = await exec_db.get_proposal(proposal_id)
    return _row_to_proposal(row)


@router.post("/run", response_model=ExecutionRunResult)
async def execution_run(force: bool = False):
    return await run_once(force=force)


@router.get("/brokers", response_model=list[BrokerStatus])
async def execution_brokers():
    out: list[BrokerStatus] = []
    for adapter in all_broker_adapters():
        out.append(
            BrokerStatus(
                broker_id=adapter.broker_id,
                name=adapter.name,
                configured=await adapter.is_configured(),
                connected=await adapter.is_connected(),
            )
        )
    return out


@router.patch("/settings", response_model=ExecutionSettingsView)
async def execution_settings_patch(body: ExecutionSettingsPatch):
    current = await get_effective_settings()
    merged = {**current}
    for field in body.model_fields:
        val = getattr(body, field)
        if val is not None:
            merged[field] = val
    if merged.get("dry_run", True):
        merged["mirror_paper"] = False
    await exec_db.save_runtime_settings(merged)
    return await _settings_view()
