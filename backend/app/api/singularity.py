"""Singularity war-room API."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from app.agents.orchestrator import orchestrator
from app.desk_auth import require_desk

router = APIRouter(tags=["singularity"])

_REFRESH_GAP = 60.0
_last_refresh = 0.0


@router.get("/api/singularity")
@router.get("/api/agents")
async def singularity_war_room(request: Request, refresh: bool = False):
    global _last_refresh
    if refresh:
        require_desk(request)
        now = time.monotonic()
        if _last_refresh and now - _last_refresh < _REFRESH_GAP:
            if orchestrator.last_result:
                report = orchestrator.agent_report()
                report["throttled"] = True
                return report
            raise HTTPException(
                status_code=429,
                detail="Odświeżenie Singularity jest ograniczone. Spróbuj za chwilę.",
            )
        _last_refresh = now
        await orchestrator.run_pipeline()
    elif not orchestrator.last_result:
        await orchestrator.run_pipeline()
    return orchestrator.agent_report()


@router.get("/api/singularity/status")
@router.get("/api/agents/status")
async def singularity_status():
    return orchestrator.roster_status()
