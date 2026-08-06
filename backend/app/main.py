"""FastAPI entrypoint — lifespan + router registration."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import register_routers
from app.api.news import initial_news
from app.db.database import init_db
from app.notifications.alert_engine import alert_engine
from app.notifications.vapid_setup import ensure_vapid_keys
from app.paper.paper_db import init_paper_db
from app.paper.portfolio_agent import sync_on_startup
from app.scheduler.jobs import scheduled_full_scan, start_scheduler, stop_scheduler
from app.scanners.opportunity_scanner import scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.growth import init_growth_db

    await init_growth_db()
    await init_paper_db()
    from app.ai.pearl_hunter.db import init_pearl_db

    await init_pearl_db()
    from app.execution.db import init_execution_db

    await init_execution_db()
    from app.telegram.predator_db import init_predator_db

    await init_predator_db()
    ensure_vapid_keys()
    try:
        from app.cycles.seasonality_monitor import run_seasonality_monitor

        run_seasonality_monitor(persist=True)
    except Exception as exc:
        logger.warning("Seasonality monitor bootstrap failed: %s", exc)
    start_scheduler()

    # Block until paper book + ledger are reconciled and agent memory seeded,
    # so the first HTTP requests never see an empty/stale portfolio race.
    try:
        await sync_on_startup()
    except Exception as exc:
        logger.warning("Portfolio sync on startup failed (will retry on schedule): %s", exc)

    async def _initial_scan() -> None:
        try:
            await scheduled_full_scan()
            if scanner.market_assessments:
                alert_engine.reset(scanner.market_assessments)
        except Exception as exc:
            logger.warning("Initial scan failed (will retry on schedule): %s", exc)

    async def _initial_pearl() -> None:
        try:
            from app.ai.pearl_hunter import run_crypto_agent, run_equity_agent
            from app.config import settings as cfg

            if not cfg.pearl_hunter_enabled:
                return
            await run_equity_agent()
            await run_crypto_agent()
        except Exception as exc:
            logger.warning("Initial pearl hunt failed (will retry on schedule): %s", exc)

    asyncio.create_task(_initial_scan())
    asyncio.create_task(initial_news())
    asyncio.create_task(_initial_pearl())
    yield
    stop_scheduler()


app = FastAPI(
    title="Cykliczny Trader Kar Digital",
    description="Cykliczny Trader · Kar Digital — cykle rynkowe, śledzenie live, powiadomienia push/SMS",
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Same-origin SPA + Vite proxy; credentials+wildcard is rejected by browsers.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)
