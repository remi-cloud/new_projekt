"""API for pearl hunter agents (global opportunity discovery)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.ai.pearl_hunter import get_pearl_status, list_pearl_finds, run_crypto_agent, run_equity_agent
from app.models.schemas import PearlFind, PearlHunterStatus

router = APIRouter(prefix="/api/pearl", tags=["pearl"])


@router.get("/status", response_model=PearlHunterStatus)
async def pearl_status():
    return await get_pearl_status()


@router.get("/finds", response_model=list[PearlFind])
async def pearl_finds(
    limit: int = Query(default=40, ge=1, le=100),
    agent_id: str | None = Query(default=None),
):
    rows = await list_pearl_finds(limit=limit, agent_id=agent_id)
    return rows


@router.post("/run")
async def pearl_run(agent: str = Query(default="both", pattern="^(equity|crypto|both)$")):
    equity: list = []
    crypto: list = []
    if agent in ("equity", "both"):
        equity = await run_equity_agent()
    if agent in ("crypto", "both"):
        crypto = await run_crypto_agent()
    return {
        "equity_count": len(equity),
        "crypto_count": len(crypto),
        "equity": equity[:10],
        "crypto": crypto[:10],
    }
