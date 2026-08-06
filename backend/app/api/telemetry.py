from fastapi import APIRouter, Query

from app.telemetry.agent_vs_spx import get_telemetry_series

router = APIRouter(tags=["telemetry"])


@router.get("/api/telemetry/agent-vs-sp500")
async def agent_vs_sp500(range: str = Query("30d", pattern="^(7d|30d|90d|all)$")):
    return await get_telemetry_series(range)
