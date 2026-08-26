"""API for Meme Universe · Launch Scout (Seed + traders + whispers)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.launch_scout.service import (
    get_launch_status,
    list_launch_candidates,
    list_launch_trader_events,
    list_launch_traders,
    list_meme_whispers,
    run_launch_scout_tick,
)

router = APIRouter(prefix="/api/launch", tags=["launch-scout"])


@router.get("/status")
async def launch_status():
    return await get_launch_status()


@router.get("/candidates")
async def launch_candidates(
    tier: str = Query(default="all", pattern="^(seed|fresh|early|watch|all)$"),
    limit: int = Query(default=50, ge=1, le=200),
):
    return {"candidates": await list_launch_candidates(tier=tier, limit=limit)}


@router.get("/whispers")
async def launch_whispers(limit: int = Query(default=20, ge=1, le=100)):
    return {"whispers": await list_meme_whispers(limit=limit)}


@router.get("/traders")
async def launch_traders(limit: int = Query(default=30, ge=1, le=50)):
    return {"traders": await list_launch_traders(limit=limit)}


@router.get("/trader-events")
async def launch_trader_events(limit: int = Query(default=40, ge=1, le=100)):
    return {"events": await list_launch_trader_events(limit=limit)}


@router.post("/run")
async def launch_run():
    result = await run_launch_scout_tick()
    if result.get("reason") == "disabled":
        raise HTTPException(status_code=503, detail="Launch Scout disabled")
    return result
