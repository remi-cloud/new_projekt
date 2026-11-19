"""Read-only desk for guests. Start, stop and settings need the desk token."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.solana_desk.learning.memory import list_lessons, public_lesson, set_status
from app.solana_desk.selftest import RateLimited, health_view, run_selftest, stored_selftest
from app.solana_desk.service import journal_csv, journal_view, set_arm, set_running, status_view, update_settings
from app.solana_desk.store import list_decisions
from app.solana_desk.stream import iter_events
from app.solana_desk.terminal import build_terminal, decision_public

router = APIRouter(prefix="/api/solana", tags=["solana-desk"])


class ControlBody(BaseModel):
    action: str = Field(min_length=4, max_length=20)


class ArmBody(BaseModel):
    armed: bool


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
    max_slippage_bps: int | None = None
    min_reserve_sol: float | None = None
    risk_per_trade_pct: float | None = None
    min_size_pct: float | None = None
    max_size_pct: float | None = None
    max_slippage_pct: float | None = None
    session_start: str | None = None
    session_end: str | None = None


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


@router.post("/arm")
async def solana_arm(body: ArmBody):
    return await set_arm(body.armed)


@router.post("/control")
async def solana_control(body: ControlBody):
    try:
        return await set_running(body.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/terminal")
async def solana_terminal():
    return await build_terminal()


@router.get("/decisions")
async def solana_decisions(
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    debug: bool = False,
):
    rows = await list_decisions(before_id=before_id, limit=limit, include_debug=debug)
    return {"decisions": [decision_public(row) for row in rows]}


@router.get("/stream")
async def solana_stream(request: Request):
    raw = request.headers.get("last-event-id") or "0"
    try:
        last_id = int(raw)
    except ValueError:
        last_id = 0

    async def body():
        async for frame in iter_events(last_id, sleep=asyncio.sleep):
            if await request.is_disconnected():
                break
            yield frame

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def solana_health():
    return await health_view()


@router.post("/selftest")
async def solana_selftest():
    try:
        return await run_selftest()
    except RateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.get("/selftest/last")
async def solana_selftest_last():
    payload = await stored_selftest()
    return payload or {"ok": None, "agents": {}, "missing": "no self-test yet"}


@router.get("/lessons")
async def solana_lessons(agent: str = "", status: str = ""):
    rows = await list_lessons(agent=agent, status=status)
    return {"lessons": [public_lesson(row) for row in rows]}


@router.post("/lessons/{lesson_id}/retire")
async def solana_lesson_retire(lesson_id: int):
    try:
        row = await set_status(lesson_id, "retired", "retired from the panel")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return public_lesson(row)


@router.post("/lessons/{lesson_id}/activate")
async def solana_lesson_activate(lesson_id: int):
    try:
        row = await set_status(lesson_id, "active")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return public_lesson(row)


@router.post("/read-marker")
async def solana_read_marker():
    from app.solana_desk.store import count_decisions, write_state

    total = await count_decisions()
    await write_state("read_marker", str(total))
    return {"line": total}


@router.post("/settings")
async def solana_settings(body: SettingsBody):
    try:
        return await update_settings(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
