import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.data.economic_calendar import fetch_economic_calendar
from app.db.database import save_opportunities
from app.db.economic_store import upsert_economic_events
from app.notifications.dispatcher import dispatch_signal_changes
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_running = False


async def run_scan_and_alert() -> dict:
    opportunities = await scanner.scan()
    result = await save_opportunities(opportunities)
    alert_result = await dispatch_signal_changes(result.get("changes") or [])
    return {**result, "alerts": alert_result}


async def scheduled_scan() -> None:
    try:
        result = await run_scan_and_alert()
        logger.info(
            "Scheduled scan complete: %s opps, %s changes, alerts=%s",
            result.get("opportunities_count"),
            result.get("changes_count"),
            result.get("alerts"),
        )
    except Exception as exc:
        logger.exception("Scheduled scan failed: %s", exc)


async def scheduled_economic_sync() -> None:
    """Background: refresh Investing-style economic calendar into SQLite."""
    try:
        events = await fetch_economic_calendar()
        n = await upsert_economic_events(events)
        logger.info("Economic calendar synced: %d events", n)
    except Exception as exc:
        logger.warning("Economic calendar sync failed: %s", exc)


def start_scheduler() -> None:
    global _running
    if _running:
        return
    scheduler.add_job(
        scheduled_scan,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="market_scan",
        replace_existing=True,
    )
    # Calendar refresh often — events move to "actual" during the day
    scheduler.add_job(
        scheduled_economic_sync,
        "interval",
        minutes=10,
        id="economic_calendar",
        replace_existing=True,
    )
    scheduler.start()
    _running = True
    logger.info(
        "Scheduler started (scan: %d min, calendar: 10 min)",
        settings.scan_interval_minutes,
    )


def stop_scheduler() -> None:
    global _running
    if _running:
        scheduler.shutdown(wait=False)
        _running = False


def is_running() -> bool:
    return _running
