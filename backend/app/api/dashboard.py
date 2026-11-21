from datetime import datetime, timezone
import logging
import time as _time

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.db.database import get_recent_opportunities, save_opportunities
from app.models.schemas import DashboardResponse, MarketSummary
from app.scheduler.jobs import is_running
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard():
    # Never await the full scan lock here — it can block for minutes and makes
    # the UI look like the server is down. Frontend keeps previous data on 503.
    if scanner.scan_in_progress and (
        not scanner.bitcoin_cycle or not scanner.market_assessments
    ):
        raise HTTPException(status_code=503, detail="Skan rynków w toku — spróbuj za chwilę")
    if not scanner.bitcoin_cycle:
        raise HTTPException(status_code=503, detail="Nie udało się pobrać danych cykli")
    if not scanner.market_assessments:
        raise HTTPException(status_code=503, detail="Skan rynków w toku — spróbuj za chwilę")

    summary = scanner.market_summary or MarketSummary(
        total_assets=0, by_signal={}, by_class={}, by_region={},
        avg_confidence=0, outlook="mixed", outlook_label="Brak danych",
    )

    return DashboardResponse(
        bitcoin_cycle=scanner.bitcoin_cycle,
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


# Guests (no desk token) may refresh the public market picture. This changes no
# desk/paper state: it only recomputes the read-only scanner snapshot, and only
# when that snapshot is stale and no refresh ran very recently. Same-origin and
# per-IP POST limits are enforced by the middleware (PUBLIC_WRITE_PATHS).
_PUBLIC_SCAN_COOLDOWN_S = 120.0
_PUBLIC_SCAN_STALE_AFTER_S = 300.0
_last_public_scan_mono = 0.0


@router.post("/api/scan/public")
async def trigger_scan_public(background_tasks: BackgroundTasks):
    global _last_public_scan_mono
    count = len(scanner.opportunities)
    if scanner.scan_in_progress:
        return {
            "scanned": False,
            "already_running": True,
            "reason": "in_progress",
            "opportunities_count": count,
        }

    stale = True
    if scanner.last_scan_at is not None:
        last = scanner.last_scan_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - last).total_seconds()
        stale = age > _PUBLIC_SCAN_STALE_AFTER_S

    now = _time.monotonic()
    within_cooldown = (now - _last_public_scan_mono) < _PUBLIC_SCAN_COOLDOWN_S
    if not stale or within_cooldown:
        return {
            "scanned": False,
            "already_running": False,
            "reason": "fresh" if not stale else "cooldown",
            "opportunities_count": count,
        }

    _last_public_scan_mono = now

    async def _run_scan() -> None:
        try:
            opportunities = await scanner.scan()
            await save_opportunities(opportunities)
        except Exception as exc:
            logging.getLogger(__name__).exception("Public scan failed: %s", exc)

    background_tasks.add_task(_run_scan)
    return {
        "scanned": True,
        "already_running": False,
        "reason": "scheduled",
        "opportunities_count": count,
    }


@router.get("/api/opportunities/history")
async def opportunity_history(limit: int = 50):
    from app.query_bounds import bounded_limit

    return await get_recent_opportunities(bounded_limit(limit, 200))
