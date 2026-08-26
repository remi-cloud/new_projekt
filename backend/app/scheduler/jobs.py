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
        await _record_agent_telemetry("full_scan")
        await _maybe_run_singularity()
    except Exception as exc:
        logger.exception("Full scan failed: %s", exc)


async def _record_agent_telemetry(scan_id: str) -> None:
    try:
        from app.telemetry.agent_vs_spx import record_telemetry_tick

        assessments = scanner.market_assessments or []
        spx = None
        for a in assessments:
            if a.symbol in ("^GSPC", "SPY"):
                spx = a.price
                break
        if spx is None:
            # Fallback: try live quotes on scanner
            quotes = getattr(scanner, "quotes", None) or {}
            q = quotes.get("^GSPC") or quotes.get("SPY")
            if q is not None:
                spx = getattr(q, "price", None) or (q.get("price") if isinstance(q, dict) else None)
        await record_telemetry_tick(assessments, spx_price=spx, scan_id=scan_id)
    except Exception as exc:
        logger.debug("Agent telemetry tick skipped: %s", exc)


async def _maybe_run_singularity() -> None:
    """Run Singularity pipeline after cycle scan (best-effort, non-blocking failures)."""
    try:
        from app.agents.orchestrator import orchestrator

        await orchestrator.run_pipeline()
        await broadcaster.publish(
            "singularity_tick",
            {
                "opportunities": len(orchestrator.opportunities),
                "last_scan_at": (
                    orchestrator.last_scan_at.isoformat()
                    if orchestrator.last_scan_at
                    else None
                ),
            },
        )
    except Exception as exc:
        logger.warning("Singularity pipeline skipped: %s", exc)


async def scheduled_price_tick() -> None:
    try:
        result = await scanner.price_tick()
        # Zawsze broadcast — frontend odświeża ceny po SSE, nawet gdy Yahoo zwróci te same wartości
        await _broadcast_state("price_tick")
        if result.get("updated", 0) > 0:
            await _maybe_notify()
            await _record_agent_telemetry("price_tick")
        await _maybe_refresh_portfolio_snapshot()
    except Exception as exc:
        logger.exception("Price tick failed: %s", exc)


async def scheduled_news_refresh() -> None:
    try:
        from app.news.macro_news import refresh_macro_news
        from app.news.news_alerts import news_alert_engine
        from app.notifications.news_dispatcher import dispatch_news_alerts

        feed, all_items = await refresh_macro_news()
        events = news_alert_engine.diff(all_items)
        if events:
            await dispatch_news_alerts(events)
        try:
            from app.notifications.social_dispatcher import queue_social_from_news_items

            social = await queue_social_from_news_items(all_items)
            if social.get("queued"):
                logger.info("Social desk (scheduled): %s", social)
        except Exception as social_exc:
            logger.debug("Social desk skipped: %s", social_exc)

        await broadcaster.publish(
            "macro_news_tick",
            {
                "fetched_at": feed.fetched_at.isoformat(),
                "fresh_count_1h": feed.fresh_count_1h,
                "counts": feed.counts,
            },
        )
        # Learn while the tape is fresh
        if getattr(settings, "ai_self_learn_on_news_refresh", True) and settings.ai_enabled:
            try:
                from app.ai.self_learn import run_self_learn_cycle

                result = await run_self_learn_cycle()
                if result.get("added"):
                    await broadcaster.publish("ai_self_learn", result)
            except Exception as learn_exc:
                logger.debug("Post-news self-learn skipped: %s", learn_exc)
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


async def scheduled_execution_tick() -> None:
    try:
        from app.config import settings as cfg
        from app.execution.agent import run_once
        from app.scanners.opportunity_scanner import scanner

        if not cfg.execution_enabled:
            return
        if scanner.scan_in_progress:
            return
        result = await run_once()
        await broadcaster.publish(
            "execution_tick",
            {
                "processed": result.processed,
                "created": result.created,
                "executed": result.executed,
                "skipped": result.skipped,
                "errors": result.errors,
            },
        )
    except Exception as exc:
        logger.exception("Execution agent tick failed: %s", exc)


async def scheduled_ai_self_learn() -> None:
    try:
        if not settings.ai_enabled or not getattr(settings, "ai_self_learn_enabled", True):
            return
        from app.ai.self_learn import run_self_learn_cycle

        result = await run_self_learn_cycle()
        if result.get("added"):
            await broadcaster.publish("ai_self_learn", result)
    except Exception as exc:
        logger.warning("AI self-learn tick failed: %s", exc)


async def scheduled_predator_poll() -> None:
    try:
        from app.telegram.predator_service import poll_predator_feed

        await poll_predator_feed(notify=True)
    except Exception as exc:
        logger.warning("Predator Telegram poll failed: %s", exc)


async def scheduled_fomo_ghost() -> None:
    try:
        from app.fomo.service import run_fomo_tick

        await run_fomo_tick()
    except Exception as exc:
        logger.warning("FOMO Ghost tick failed: %s", exc)


async def scheduled_launch_scout() -> None:
    try:
        from app.launch_scout.service import run_launch_scout_tick

        await run_launch_scout_tick()
    except Exception as exc:
        logger.warning("Launch Scout tick failed: %s", exc)


async def scheduled_axiom() -> None:
    try:
        from app.axiom.service import run_axiom_tick

        await run_axiom_tick()
    except Exception as exc:
        logger.warning("Axiom tick failed: %s", exc)


async def scheduled_coordinator() -> None:
    try:
        from app.coordinator.service import run_coordinator_tick

        await run_coordinator_tick()
    except Exception as exc:
        logger.warning("Coordinator tick failed: %s", exc)


async def scheduled_binance_ai_bot() -> None:
    try:
        from app.integrations.binance_ai_agent import run_binance_ai_tick

        await run_binance_ai_tick()
    except Exception as exc:
        logger.warning("Binance AI BOT tick failed: %s", exc)


async def scheduled_seasonality_monitor() -> None:
    try:
        from app.cycles.seasonality_monitor import run_seasonality_monitor

        health = run_seasonality_monitor(persist=True)
        await broadcaster.publish("seasonality_health", health)
    except Exception as exc:
        logger.warning("Seasonality monitor failed: %s", exc)


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
    scheduler.add_job(
        scheduled_execution_tick,
        "interval",
        minutes=max(5, int(settings.execution_tick_minutes)),
        id="execution_agent_tick",
        replace_existing=True,
    )
    if getattr(settings, "ai_self_learn_enabled", True) and settings.ai_enabled:
        scheduler.add_job(
            scheduled_ai_self_learn,
            "interval",
            minutes=max(15, int(settings.ai_self_learn_interval_minutes)),
            id="ai_self_learn",
            replace_existing=True,
        )
    if getattr(settings, "telegram_bot_token", "") and (
        getattr(settings, "telegram_predator_enabled", True)
        or getattr(settings, "fomo_telegram_enabled", True)
    ):
        scheduler.add_job(
            scheduled_predator_poll,
            "interval",
            seconds=max(30, int(settings.telegram_predator_interval_seconds)),
            id="telegram_predator_poll",
            replace_existing=True,
        )
    if getattr(settings, "fomo_enabled", True):
        scheduler.add_job(
            scheduled_fomo_ghost,
            "interval",
            seconds=max(60, int(getattr(settings, "fomo_interval_seconds", 60) or 60)),
            id="fomo_ghost_tick",
            replace_existing=True,
        )
    if getattr(settings, "launch_scout_enabled", True):
        scheduler.add_job(
            scheduled_launch_scout,
            "interval",
            seconds=max(60, int(getattr(settings, "launch_scout_interval_seconds", 60) or 60)),
            id="launch_scout_tick",
            replace_existing=True,
        )
    if getattr(settings, "axiom_enabled", True):
        scheduler.add_job(
            scheduled_axiom,
            "interval",
            seconds=max(60, int(getattr(settings, "axiom_interval_seconds", 90) or 90)),
            id="axiom_tick",
            replace_existing=True,
        )
    scheduler.add_job(
        scheduled_coordinator,
        "interval",
        seconds=max(60, int(getattr(settings, "coordinator_interval_seconds", 300) or 300)),
        id="coordinator_tick",
        replace_existing=True,
    )
    if getattr(settings, "binance_ai_bot_enabled", True):
        scheduler.add_job(
            scheduled_binance_ai_bot,
            "interval",
            seconds=max(60, int(getattr(settings, "binance_ai_bot_interval_seconds", 120) or 120)),
            id="binance_ai_bot_tick",
            replace_existing=True,
        )
    scheduler.add_job(
        scheduled_seasonality_monitor,
        "interval",
        days=7,
        id="seasonality_monitor_weekly",
        replace_existing=True,
    )
    scheduler.start()
    _running = True
    _initialised = True
    logger.info(
        "Scheduler started — prices every %ds, news every %ds, full scan every %d min, "
        "autosave every %ds, pearl equity %d min, pearl crypto %d min, execution %d min, "
        "ai self-learn %d min, predator telegram %ds, fomo ghost %ds, launch scout %ds, axiom %ds",
        settings.price_poll_interval_seconds,
        settings.news_refresh_interval_seconds,
        settings.scan_interval_minutes,
        settings.auto_backup_interval_seconds if settings.auto_backup_enabled else 0,
        settings.pearl_equity_interval_minutes if settings.pearl_hunter_enabled else 0,
        settings.pearl_crypto_interval_minutes if settings.pearl_hunter_enabled else 0,
        settings.execution_tick_minutes,
        settings.ai_self_learn_interval_minutes if settings.ai_self_learn_enabled else 0,
        settings.telegram_predator_interval_seconds
        if getattr(settings, "telegram_bot_token", "")
        else 0,
        max(60, int(getattr(settings, "fomo_interval_seconds", 60) or 60))
        if getattr(settings, "fomo_enabled", True)
        else 0,
        max(60, int(getattr(settings, "launch_scout_interval_seconds", 60) or 60))
        if getattr(settings, "launch_scout_enabled", True)
        else 0,
        max(60, int(getattr(settings, "axiom_interval_seconds", 90) or 90))
        if getattr(settings, "axiom_enabled", True)
        else 0,
    )


def stop_scheduler() -> None:
    global _running
    if _running:
        scheduler.shutdown(wait=False)
        _running = False


def is_running() -> bool:
    return _running
