"""API for Meme Universe · Launch Scout (Seed + traders + whispers)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.launch_scout.dex_arena import get_dex_arena_snapshot
from app.launch_scout.service import (
    get_launch_status,
    list_launch_candidates,
    list_launch_trader_events,
    list_launch_traders,
    list_meme_whispers,
    run_launch_scout_tick,
)
from app.launch_scout.wallet_scout import bags_for_wallet, get_wallet_scout_snapshot

router = APIRouter(prefix="/api/launch", tags=["launch-scout"])


@router.get("/status")
async def launch_status():
    return await get_launch_status()


@router.get("/candidates")
async def launch_candidates(
    tier: str = Query(default="all", pattern="^(seed|fresh|early|watch|all)$"),
    dex: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    return {
        "candidates": await list_launch_candidates(tier=tier, limit=limit, dex=dex),
        "dex": dex,
    }


@router.get("/dex-arena")
async def launch_dex_arena():
    return await get_dex_arena_snapshot()


@router.get("/session-clock")
async def launch_session_clock():
    from app.cycles.session_clock import get_session_clock_snapshot

    return await get_session_clock_snapshot()


@router.get("/whispers")
async def launch_whispers(limit: int = Query(default=20, ge=1, le=100)):
    return {"whispers": await list_meme_whispers(limit=limit)}


@router.get("/traders")
async def launch_traders(limit: int = Query(default=30, ge=1, le=50)):
    return {"traders": await list_launch_traders(limit=limit)}


@router.get("/traders/{wallet}/bags")
async def launch_trader_bags(
    wallet: str,
    include_closed: bool = Query(default=True),
):
    w = (wallet or "").strip()
    if len(w) < 20:
        raise HTTPException(status_code=400, detail="Invalid wallet")
    return await bags_for_wallet(w, include_closed=include_closed)


@router.get("/wallet-scout")
async def launch_wallet_scout(limit: int = Query(default=15, ge=1, le=30)):
    return await get_wallet_scout_snapshot(limit=limit)


@router.get("/trader-events")
async def launch_trader_events(limit: int = Query(default=40, ge=1, le=100)):
    return {"events": await list_launch_trader_events(limit=limit)}


@router.post("/run")
async def launch_run():
    result = await run_launch_scout_tick()
    if result.get("reason") == "disabled":
        raise HTTPException(status_code=503, detail="Launch Scout disabled")
    return result
