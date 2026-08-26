"""Coordinator health API."""

from __future__ import annotations

from fastapi import APIRouter

from app.coordinator.service import get_coordinator_health, run_coordinator_tick

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])


@router.get("/health")
async def coordinator_health():
    return await get_coordinator_health()


@router.post("/run")
async def coordinator_run():
    return await run_coordinator_tick()
