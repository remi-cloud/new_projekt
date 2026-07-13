import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db.database import get_alert_settings, save_opportunities
from app.notifications.alert_engine import alert_engine
from app.notifications.dispatcher import dispatch_alerts
from app.realtime.broadcaster import broadcaster
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_running = False
_initialised = False


async def scheduled_full_scan() -> None:
    try:
        opportunities = await scanner.scan()
        await save_opportunities(opportunities)
        await _maybe_notify()
        await _broadcast_state("full_scan")
    except Exception as exc:
        logger.exception("Full scan failed: %s", exc)


async def scheduled_price_tick() -> None:
    try:
        result = await scanner.price_tick()
        if result.get("updated", 0) > 0:
            await _maybe_notify()
            await _broadcast_state("price_tick")
    except Exception as exc:
        logger.exception("Price tick failed: %s", exc)


async def _maybe_notify() -> None:
    if not settings.notifications_enabled or not scanner.market_assessments:
        return
    alert_settings = await get_alert_settings()
    if not alert_settings.get("push_enabled") and not alert_settings.get("sms_enabled") and not alert_settings.get("ntfy_enabled"):
        return
    events = alert_engine.diff(
        scanner.market_assessments,
        min_confidence=alert_settings.get("min_confidence", settings.alert_min_confidence),
    )
    if events:
        await dispatch_alerts(events)


async def _broadcast_state(event_type: str) -> None:
    await broadcaster.publish(
        event_type,
        {
            "quotes_count": len(scanner.quotes),
            "last_scan_at": scanner.last_scan_at.isoformat() if scanner.last_scan_at else None,
            "last_price_tick_at": (
                scanner.last_price_tick_at.isoformat() if scanner.last_price_tick_at else None
            ),
            "live_mode": scanner.live_mode,
            "summary": scanner.market_summary.model_dump() if scanner.market_summary else None,
        },
    )
    if scanner.quotes:
        top = sorted(scanner.quotes, key=lambda q: q.updated_at, reverse=True)[:20]
        await broadcaster.publish(
            "prices",
            [
                {
                    "symbol": q.symbol,
                    "price": q.price,
                    "change_pct_24h": q.change_pct_24h,
                    "updated_at": q.updated_at.isoformat(),
                }
                for q in top
            ],
        )


def start_scheduler() -> None:
    global _running, _initialised
    if _running:
        return

    scheduler.add_job(
        scheduled_full_scan,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="full_market_scan",
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_price_tick,
        "interval",
        seconds=settings.price_poll_interval_seconds,
        id="price_ticker",
        replace_existing=True,
    )
    scheduler.start()
    _running = True
    _initialised = True
    logger.info(
        "Scheduler started — prices every %ds, full scan every %d min",
        settings.price_poll_interval_seconds,
        settings.scan_interval_minutes,
    )


def stop_scheduler() -> None:
    global _running
    if _running:
        scheduler.shutdown(wait=False)
        _running = False


def is_running() -> bool:
    return _running
