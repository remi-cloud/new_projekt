"""Read-only desk for guests. Start, stop and settings need the desk token."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.solana_desk.service import journal_csv, journal_view, set_running, status_view, update_settings

router = APIRouter(prefix="/api/solana", tags=["solana-desk"])


class ControlBody(BaseModel):
    action: str = Field(min_length=4, max_length=20)


class SettingsBody(BaseModel):
    starting_sol: float | None = None
    starting_usd: float | None = None
    position_sol: float | None = None
    max_per_trade_sol: float | None = None
    daily_loss_sol: float | None = None
    stop_pct: float | None = None
    take_profit_pct: float | None = None
    trail_activate_pct: float | None = None
    trail_gap_pct: float | None = None
    time_stop_minutes: int | None = None
    max_open: int | None = None
    min_liquidity_usd: float | None = None
    min_age_minutes: float | None = None
    max_age_hours: float | None = None
    min_volume_usd: float | None = None
    max_top_holder_pct: float | None = None
    max_top10_pct: float | None = None
    max_dev_pct: float | None = None
    max_tax_pct: float | None = None
    priority_fee_sol: float | None = None
    pump_fee_rate: float | None = None
    slippage_base_bps: float | None = None


@router.get("/status")
async def solana_status():
    return await status_view()


@router.get("/journal")
async def solana_journal(limit: int = Query(default=40, ge=1, le=200)):
    return await journal_view(limit)


@router.get("/trades.csv")
async def solana_trades_csv():
    body = await journal_csv()
    return PlainTextResponse(
        body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=solana-desk.csv"},
    )


@router.post("/control")
async def solana_control(body: ControlBody):
    try:
        return await set_running(body.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/settings")
async def solana_settings(body: SettingsBody):
    try:
        return await update_settings(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
