"""Singularity war-room API."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.orchestrator import orchestrator
from app.read_guard import forced_refresh_due

router = APIRouter(tags=["singularity"])


@router.get("/api/singularity")
@router.get("/api/agents")
async def singularity_war_room(refresh: bool = False):
    if refresh and not forced_refresh_due("singularity"):
        report = orchestrator.agent_report()
        if isinstance(report, dict):
            return {**report, "refresh_cached": True}
        return report
    if refresh or not orchestrator.last_result:
        await orchestrator.run_pipeline()
    return orchestrator.agent_report()


@router.get("/api/singularity/status")
@router.get("/api/agents/status")
async def singularity_status():
    return orchestrator.roster_status()
