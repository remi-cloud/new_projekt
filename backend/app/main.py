import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import (
    get_recent_opportunities,
    get_scan_history,
    get_signal_changes,
    init_db,
    save_opportunities,
)
from app.models.schemas import DashboardResponse, HistoryResponse
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
    description=(
        "Skaner rynkowy oparty na cyklu Bitcoin (364/1064 dni) "
        "i cyklu prezydenckim USA — okazje kupna/sprzedaży 24/7."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "scanner_running": is_running(),
        "last_scan_at": scanner.last_scan_at.isoformat() if scanner.last_scan_at else None,
        "opportunities_count": len(scanner.opportunities),
    }


@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard():
    if not scanner.bitcoin_cycle or not scanner.presidential_cycle or not scanner.quotes:
        await scanner.scan()
    if not scanner.bitcoin_cycle or not scanner.presidential_cycle:
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
    result = await save_opportunities(opportunities)
    return {"scanned": True, **result}


@app.get("/api/opportunities/history")
async def opportunity_history(limit: int = Query(50, ge=1, le=500)):
    return await get_recent_opportunities(limit)


@app.get("/api/history", response_model=HistoryResponse)
async def history(
    scans: int = Query(20, ge=1, le=100),
    changes: int = Query(50, ge=1, le=200),
    opportunities: int = Query(50, ge=1, le=200),
):
    return HistoryResponse(
        scans=await get_scan_history(scans),
        changes=await get_signal_changes(changes),
        recent_opportunities=await get_recent_opportunities(opportunities),
    )


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
