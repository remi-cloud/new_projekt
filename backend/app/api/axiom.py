"""API for Axiom desk (Pulse + all positions)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.axiom import get_axiom_status, list_axiom_positions, list_axiom_pulse, run_axiom_tick

router = APIRouter(prefix="/api/axiom", tags=["axiom"])


@router.get("/status")
async def axiom_status():
    return await get_axiom_status()


@router.get("/pulse")
async def axiom_pulse(limit: int = Query(default=80, ge=1, le=200)):
    return {"markets": await list_axiom_pulse(limit=limit)}


@router.get("/positions")
async def axiom_positions(
    limit: int = Query(default=200, ge=1, le=500),
    status: str | None = Query(default="all", pattern="^(open|closed|all)$"),
    owner_kind: str | None = Query(default=None, pattern="^(fomo_family|wallet|kar_digital)$"),
):
    return {
        "positions": await list_axiom_positions(
            limit=limit,
            status=status,
            owner_kind=owner_kind,
        )
    }


@router.post("/run")
async def axiom_run():
    result = await run_axiom_tick()
    if result.get("reason") == "disabled":
        raise HTTPException(status_code=503, detail="Axiom desk disabled")
    return result
