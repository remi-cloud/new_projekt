import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db.database import get_recent_opportunities, init_db
from app.data.chart_data import CHART_PRESETS, fetch_chart
from app.models.schemas import ChartResponse, DashboardResponse, MarketSummary, RegionalCycleSnapshot
from app.scheduler.jobs import is_running, scheduled_scan, start_scheduler, stop_scheduler
from app.scanners.opportunity_scanner import scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


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
    description="Aplikacja tradingowa oparta na cyklu Bitcoin (364/1064 dni) i regionalnych cyklach makro",
    version="1.2.0",
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
    return {"status": "ok", "scanner_running": is_running(), "www": STATIC_DIR.exists()}


@app.get("/api/dashboard", response_model=DashboardResponse)
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
        scanner_running=is_running(),
    )


@app.get("/api/markets/assessments")
async def market_assessments(
    region: str | None = None,
    asset_class: str | None = None,
    signal: str | None = None,
):
    if not scanner.market_assessments:
        await scanner.scan()
    results = scanner.market_assessments
    if region:
        results = [a for a in results if a.region == region]
    if asset_class:
        results = [a for a in results if a.asset_class.value == asset_class]
    if signal:
        results = [a for a in results if a.signal.value == signal]
    return results


@app.get("/api/markets/chart/{symbol:path}", response_model=ChartResponse)
async def market_chart(symbol: str, range: str = "3M"):
    if range not in CHART_PRESETS:
        range = "3M"
    chart = await fetch_chart(symbol, range)
    if not chart:
        raise HTTPException(status_code=404, detail=f"Brak danych wykresu dla {symbol}")
    return chart


@app.get("/api/markets/chart-presets")
async def chart_presets():
    return list(CHART_PRESETS.keys())


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


@app.get("/api/cycles/regional", response_model=list[RegionalCycleSnapshot])
async def regional_cycles():
    if not scanner.regional_cycles:
        await scanner.scan()
    return scanner.regional_cycles


# ── WWW: serwowanie frontendu SPA ──
if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")

    logger.info("WWW frontend enabled from %s", STATIC_DIR)
else:
    logger.info("No static frontend at %s — API-only mode", STATIC_DIR)
