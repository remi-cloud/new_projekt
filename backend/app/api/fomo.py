"""API for FOMO Ghost agent (Cope Capital / fomo.family top portfolios)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.fomo import get_fomo_status, list_fomo_events, list_fomo_top, register_cope_key, run_fomo_tick
from app.fomo.bags import family_summary, list_family_bags
from app.fomo.telegram import fomo_telegram_status

router = APIRouter(prefix="/api/fomo", tags=["fomo"])


class FomoRegisterBody(BaseModel):
    agent_name: str = Field(default="cyclical-trader-fomo-ghost", max_length=80)


@router.get("/status")
async def fomo_status():
    st = await get_fomo_status()
    try:
        st["telegram"] = await fomo_telegram_status()
        st["family"] = await family_summary()
    except Exception:
        pass
    return st


@router.get("/top")
async def fomo_top(limit: int = Query(default=30, ge=1, le=50)):
    return {"traders": await list_fomo_top(limit=limit)}


@router.get("/events")
async def fomo_events(
    limit: int = Query(default=50, ge=1, le=200),
    side: str | None = Query(default=None, pattern="^(buy|sell)$"),
):
    return {"events": await list_fomo_events(limit=limit, side=side)}


@router.get("/bags")
async def fomo_bags(
    limit: int = Query(default=100, ge=1, le=500),
    include_closed: bool = Query(default=False),
    handle: str | None = Query(default=None, max_length=64),
):
    bags = await list_family_bags(
        include_closed=include_closed,
        limit=limit,
        handle=handle,
    )
    return {"bags": bags, "summary": await family_summary()}


@router.get("/family")
async def fomo_family(limit: int = Query(default=100, ge=1, le=500)):
    """FOMO Family open bags reconstructed from Cope + Telegram activity."""
    bags = await list_family_bags(include_closed=False, limit=limit)
    return {"family": "fomo.family", "bags": bags, "summary": await family_summary()}


@router.get("/telegram")
async def fomo_telegram():
    return await fomo_telegram_status()


@router.post("/run")
async def fomo_run(force: bool = Query(default=False)):
    result = await run_fomo_tick(force_activity=force)
    if result.get("reason") == "disabled":
        raise HTTPException(status_code=503, detail="FOMO Ghost disabled")
    if result.get("reason") == "needs_api_key":
        err = str(result.get("error") or "").strip()
        raise HTTPException(status_code=503, detail=(err or "Cope API key missing")[:400])
    return result


@router.post("/register")
async def fomo_register(body: FomoRegisterBody | None = None):
    try:
        return await register_cope_key(agent_name=(body.agent_name if body else "cyclical-trader-fomo-ghost"))
    except Exception as exc:
        from app.fomo.offline import humanize_cope_error, is_cope_unreachable
        from app.fomo.service import run_degraded_tick

        if is_cope_unreachable(exc):
            degraded = await run_degraded_tick(reason=str(exc))
            return {
                "ok": True,
                "mode": "degraded",
                "api_key_saved": False,
                "upstream_error": humanize_cope_error(exc),
                "degraded": degraded,
            }
        raise HTTPException(status_code=502, detail=humanize_cope_error(exc)[:400]) from exc
