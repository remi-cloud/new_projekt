import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db.database import save_opportunities
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
    scheduler.start()
    _running = True
    logger.info("Scheduler started (interval: %d min)", settings.scan_interval_minutes)


def stop_scheduler() -> None:
    global _running
    if _running:
        scheduler.shutdown(wait=False)
        _running = False


def is_running() -> bool:
    return _running
