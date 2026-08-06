"""Superokazje + whale flows API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.data.whale_flows import fetch_whale_snapshot
from app.models.schemas import SuperOpportunitiesResponse, SuperOpportunity
from app.scanners.super_opportunities import (
    build_super_opportunities,
    build_super_opportunity,
    resolve_opportunity_for_symbol,
)

router = APIRouter(tags=["super-opportunities"])


@router.get("/api/super-opportunities", response_model=SuperOpportunitiesResponse)
async def list_super_opportunities(
    min_score: float = Query(default=0, ge=0, le=100),
):
    data = await build_super_opportunities(min_score=min_score)
    return SuperOpportunitiesResponse(**data)


@router.get("/api/super-opportunities/{symbol}", response_model=SuperOpportunity)
async def get_super_opportunity(symbol: str):
    opp = await resolve_opportunity_for_symbol(symbol)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")
    try:
        data = await build_super_opportunity(opp, include_heatmap_3d=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SuperOpportunity(**data)


@router.get("/api/whale-flows")
async def whale_flows(force: bool = False):
    by_sym = await fetch_whale_snapshot(force=force)
    return {
        "count": len(by_sym),
        "items": list(by_sym.values()),
        "by_symbol": by_sym,
    }
