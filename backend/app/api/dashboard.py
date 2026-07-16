from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.db.database import get_recent_opportunities, save_opportunities
from app.models.schemas import DashboardResponse, MarketSummary
from app.scheduler.jobs import is_running
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard():
    if not scanner.bitcoin_cycle or not scanner.market_assessments:
        await scanner.scan()
    if not scanner.bitcoin_cycle or not scanner.presidential_cycle:
        raise HTTPException(status_code=503, detail="Nie udało się pobrać danych cykli")

    summary = scanner.market_summary or MarketSummary(
        total_assets=0, by_signal={}, by_class={}, by_region={},
        avg_confidence=0, outlook="mixed", outlook_label="Brak danych",
    )

    return DashboardResponse(
        bitcoin_cycle=scanner.bitcoin_cycle,
        presidential_cycle=scanner.presidential_cycle,
        regional_cycles=scanner.regional_cycles,
        opportunities=scanner.opportunities,
        monitored_assets=scanner.quotes,
        market_assessments=scanner.market_assessments,
        market_summary=summary,
        last_scan_at=scanner.last_scan_at,
        last_price_tick_at=scanner.last_price_tick_at,
        live_mode=scanner.live_mode,
        scanner_running=is_running(),
        scan_in_progress=scanner.scan_in_progress,
    )


@router.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    if scanner.scan_in_progress:
        return {
            "scanned": False,
            "background": True,
            "already_running": True,
            "opportunities_count": len(scanner.opportunities),
        }

    async def _run_scan() -> None:
        try:
            opportunities = await scanner.scan()
            await save_opportunities(opportunities)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception("Background scan failed: %s", exc)

    background_tasks.add_task(_run_scan)
    return {
        "scanned": True,
        "background": True,
        "already_running": False,
        "opportunities_count": len(scanner.opportunities),
    }


@router.get("/api/opportunities/history")
async def opportunity_history(limit: int = 50):
    return await get_recent_opportunities(limit)
