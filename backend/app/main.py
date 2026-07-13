import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import get_recent_opportunities, init_db
from app.models.schemas import DashboardResponse
from app.scheduler.jobs import is_running, scheduled_scan, start_scheduler, stop_scheduler
from app.scanners.opportunity_scanner import scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    try:
        await scheduled_scan()
    except Exception as exc:
        logger.warning("Initial scan failed (will retry on schedule): %s", exc)
    yield
    stop_scheduler()


app = FastAPI(
    title="Cyclical Trader",
    description="Aplikacja tradingowa oparta na cyklu Bitcoin (364/1064 dni) i cyklu prezydenckim USA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "scanner_running": is_running()}


@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard():
    if not scanner.bitcoin_cycle or not scanner.presidential_cycle or not scanner.quotes:
        await scanner.scan()
    if not scanner.bitcoin_cycle or not scanner.presidential_cycle:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Nie udało się pobrać danych cykli")
    return DashboardResponse(
        bitcoin_cycle=scanner.bitcoin_cycle,
        presidential_cycle=scanner.presidential_cycle,
        opportunities=scanner.opportunities,
        monitored_assets=scanner.quotes,
        last_scan_at=scanner.last_scan_at,
        scanner_running=is_running(),
    )


@app.post("/api/scan")
async def trigger_scan():
    opportunities = await scanner.scan()
    from app.db.database import save_opportunities
    await save_opportunities(opportunities)
    return {"scanned": True, "opportunities_count": len(opportunities)}


@app.get("/api/opportunities/history")
async def opportunity_history(limit: int = 50):
    return await get_recent_opportunities(limit)


@app.get("/api/cycles/bitcoin")
async def bitcoin_cycle():
    if not scanner.bitcoin_cycle:
        await scanner.scan()
    return scanner.bitcoin_cycle


@app.get("/api/cycles/presidential")
async def presidential_cycle():
    if not scanner.presidential_cycle:
        await scanner.scan()
    return scanner.presidential_cycle
