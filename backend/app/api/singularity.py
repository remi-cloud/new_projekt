"""Singularity war-room API."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.orchestrator import orchestrator

router = APIRouter(tags=["singularity"])


@router.get("/api/singularity")
@router.get("/api/agents")
async def singularity_war_room(refresh: bool = False):
    if refresh or not orchestrator.last_result:
        await orchestrator.run_pipeline()
    return orchestrator.agent_report()


@router.get("/api/singularity/status")
@router.get("/api/agents/status")
async def singularity_status():
    return orchestrator.roster_status()
