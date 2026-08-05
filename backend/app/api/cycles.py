from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.cycles.calendar_seasonality import (
    get_instrument_calendar,
    get_month_pumps,
    month_pump_snippet,
    search_catalog,
)
from app.cycles.global_cycle_book import get_global_cycle_book
from app.cycles.intramonth_seasonality import get_intramonth
from app.cycles.seasonality_monitor import get_health, run_seasonality_monitor
from app.models.schemas import RegionalCycleSnapshot
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["cycles"])


@router.get("/api/cycles/bitcoin")
async def bitcoin_cycle():
    if not scanner.bitcoin_cycle:
        await scanner.scan()
    return scanner.bitcoin_cycle


@router.get("/api/cycles/presidential")
async def presidential_cycle():
    if not scanner.presidential_cycle:
        await scanner.scan()
    return scanner.presidential_cycle


@router.get("/api/cycles/regional", response_model=list[RegionalCycleSnapshot])
async def regional_cycles():
    if not scanner.regional_cycles:
        await scanner.scan()
    return scanner.regional_cycles


@router.get("/api/cycles/seasonality-health")
async def seasonality_health(refresh: bool = False):
    """Drift status for presidential/BTC seasonality matrices."""
    if refresh or not get_health().get("last_run"):
        return run_seasonality_monitor(persist=True)
    return get_health()


@router.get("/api/cycles/intramonth")
async def intramonth_seasonality(
    month: int = Query(..., ge=1, le=12),
    universe: str = Query("us", pattern="^(us|btc)$"),
):
    """Day-of-month (1–31) + week-of-month (1–4) seasonality for US EW or BTC."""
    try:
        return get_intramonth(universe, month)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/cycles/global-book")
async def global_cycle_book(
    status: Literal["all", "adopted", "watch", "rejected"] = Query("all"),
):
    """Cross-market seasonality order book (monthly / weekly / yearly windows).

    Field scouts run the same equal-weight rules on us/eu/asia/em/pl/crypto.
    Adopted entries reproduced on enough markets to enter the project book.
    """
    return get_global_cycle_book(status=status)


@router.get("/api/cycles/instrument-calendar")
async def instrument_calendar(symbol: str = Query(..., min_length=1)):
    """12-month calendar seasonality profile for one instrument."""
    data = get_instrument_calendar(symbol)
    if not data.get("available"):
        raise HTTPException(status_code=404, detail=f"No calendar seasonality for {symbol}")
    return data


@router.get("/api/cycles/month-pumps")
async def month_pumps(
    month: int = Query(..., ge=1, le=12),
    asset_class: str | None = Query(None, alias="class"),
    region: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    direction: Literal["up", "down", "both"] = "both",
):
    """Assets historically pumped / drained in a calendar month."""
    try:
        return get_month_pumps(
            month,
            asset_class=asset_class,
            region=region,
            limit=limit,
            direction=direction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/cycles/month-pumps/snippet")
async def month_pumps_snippet(
    month: int = Query(..., ge=1, le=12),
    top_n: int = Query(3, ge=1, le=10),
):
    """Short top-pumped / drained blurb for embedding under month strips."""
    return month_pump_snippet(month, top_n=top_n)


@router.get("/api/cycles/calendar-search")
async def calendar_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Symbol/name search for seasonality info window."""
    return {"query": q, "results": search_catalog(q, limit=limit)}
