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
        # Zawsze broadcast — frontend odświeża ceny po SSE, nawet gdy Yahoo zwróci te same wartości
        await _broadcast_state("price_tick")
        if result.get("updated", 0) > 0:
            await _maybe_notify()
        await _maybe_refresh_portfolio_snapshot()
    except Exception as exc:
        logger.exception("Price tick failed: %s", exc)


async def scheduled_news_refresh() -> None:
    try:
        from app.news.macro_news import refresh_macro_news

        feed, _ = await refresh_macro_news()
        await broadcaster.publish(
            "macro_news_tick",
            {
                "fetched_at": feed.fetched_at.isoformat(),
                "fresh_count_1h": feed.fresh_count_1h,
                "counts": feed.counts,
            },
        )
    except Exception as exc:
        logger.exception("News refresh failed: %s", exc)


async def _maybe_refresh_portfolio_snapshot() -> None:
    from app.paper import paper_db
    from app.paper.limit_orders import process_limit_orders
    from app.paper.portfolio_agent import refresh_snapshot
    from app.paper.pricing import refresh_quotes_for_symbols

    try:
        await process_limit_orders()
    except Exception as exc:
        logger.debug("Limit order processing skipped: %s", exc)

    positions = await paper_db.get_positions()
    pending = await paper_db.get_pending_limit_orders()
    symbols = {p["symbol"] for p in positions} | {o["symbol"] for o in pending}
    if not symbols:
        return
    try:
        await refresh_quotes_for_symbols(list(symbols))
        await refresh_snapshot()
    except Exception as exc:
        logger.debug("Portfolio snapshot refresh skipped: %s", exc)


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


async def scheduled_progress_autosave() -> None:
    try:
        from app.backup import backup_enabled, save_progress

        if not backup_enabled():
            return
        save_progress(reason="scheduled")
    except Exception as exc:
        logger.exception("Progress autosave failed: %s", exc)


async def scheduled_pearl_equity() -> None:
    try:
        from app.ai.pearl_hunter import run_equity_agent
        from app.config import settings as cfg

        if not cfg.pearl_hunter_enabled:
            return
        finds = await run_equity_agent()
        await broadcaster.publish(
            "pearl_tick",
            {"agent": "pearl_equity", "count": len(finds)},
        )
    except Exception as exc:
        logger.exception("Pearl equity agent failed: %s", exc)


async def scheduled_pearl_crypto() -> None:
    try:
        from app.ai.pearl_hunter import run_crypto_agent
        from app.config import settings as cfg

        if not cfg.pearl_hunter_enabled:
            return
        finds = await run_crypto_agent()
        await broadcaster.publish(
            "pearl_tick",
            {"agent": "pearl_crypto", "count": len(finds)},
        )
    except Exception as exc:
        logger.exception("Pearl crypto agent failed: %s", exc)


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
    scheduler.add_job(
        scheduled_news_refresh,
        "interval",
        seconds=settings.news_refresh_interval_seconds,
        id="macro_news_refresh",
        replace_existing=True,
    )
    if getattr(settings, "auto_backup_enabled", True):
        scheduler.add_job(
            scheduled_progress_autosave,
            "interval",
            seconds=max(10, int(settings.auto_backup_interval_seconds)),
            id="progress_autosave",
            replace_existing=True,
        )
    if getattr(settings, "pearl_hunter_enabled", True):
        scheduler.add_job(
            scheduled_pearl_equity,
            "interval",
            minutes=max(10, int(settings.pearl_equity_interval_minutes)),
            id="pearl_equity_hunter",
            replace_existing=True,
        )
        scheduler.add_job(
            scheduled_pearl_crypto,
            "interval",
            minutes=max(10, int(settings.pearl_crypto_interval_minutes)),
            id="pearl_crypto_hunter",
            replace_existing=True,
        )
    scheduler.start()
    _running = True
    _initialised = True
    logger.info(
        "Scheduler started — prices every %ds, news every %ds, full scan every %d min, "
        "autosave every %ds, pearl equity %d min, pearl crypto %d min",
        settings.price_poll_interval_seconds,
        settings.news_refresh_interval_seconds,
        settings.scan_interval_minutes,
        settings.auto_backup_interval_seconds if settings.auto_backup_enabled else 0,
        settings.pearl_equity_interval_minutes if settings.pearl_hunter_enabled else 0,
        settings.pearl_crypto_interval_minutes if settings.pearl_hunter_enabled else 0,
    )


def stop_scheduler() -> None:
    global _running
    if _running:
        scheduler.shutdown(wait=False)
        _running = False


def is_running() -> bool:
    return _running
