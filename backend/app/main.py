import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data.assets import DEFAULT_ASSETS
from app.db.database import (
    get_recent_opportunities,
    get_scan_history,
    get_signal_changes,
    init_db,
)
from app.db.settings_store import (
    add_watchlist_item,
    get_alert_log,
    get_alert_settings,
    get_watchlist,
    remove_watchlist_item,
    reset_watchlist,
    save_alert_settings,
    set_watchlist_enabled,
)
from app.models.schemas import (
    AlertSettings,
    DashboardResponse,
    HistoryResponse,
    WatchlistAddRequest,
    WatchlistToggleRequest,
)
from app.notifications.dispatcher import dispatch_signal_changes, send_test_alert
from app.scheduler.jobs import is_running, run_scan_and_alert, scheduled_scan, start_scheduler, stop_scheduler
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
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "scanner_running": is_running(),
        "last_scan_at": scanner.last_scan_at.isoformat() if scanner.last_scan_at else None,
        "opportunities_count": len(scanner.opportunities),
        "version": "1.2.0",
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
    result = await run_scan_and_alert()
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


# --- Watchlist ---


@app.get("/api/watchlist")
async def watchlist():
    items = await get_watchlist()
    return {
        "items": [
            {**item, "enabled": bool(item.get("enabled", 1))}
            for item in items
        ],
        "catalog": DEFAULT_ASSETS,
    }


@app.post("/api/watchlist")
async def watchlist_add(body: WatchlistAddRequest):
    item = await add_watchlist_item(
        body.symbol,
        body.name,
        body.asset_class.value if body.asset_class else None,
    )
    return {**item, "enabled": bool(item.get("enabled", 1))}


@app.delete("/api/watchlist/{symbol}")
async def watchlist_remove(symbol: str):
    removed = await remove_watchlist_item(symbol)
    if not removed:
        raise HTTPException(status_code=404, detail="Symbol nie jest na watchliście")
    return {"removed": True, "symbol": symbol}


@app.patch("/api/watchlist/{symbol}")
async def watchlist_toggle(symbol: str, body: WatchlistToggleRequest):
    item = await set_watchlist_enabled(symbol, body.enabled)
    if not item:
        raise HTTPException(status_code=404, detail="Symbol nie jest na watchliście")
    return {**item, "enabled": bool(item.get("enabled", 1))}


@app.post("/api/watchlist/reset")
async def watchlist_reset():
    items = await reset_watchlist()
    return {
        "items": [{**item, "enabled": bool(item.get("enabled", 1))} for item in items]
    }


# --- Alerts ---


@app.get("/api/alerts/settings", response_model=AlertSettings)
async def alerts_settings_get():
    return await get_alert_settings()


@app.put("/api/alerts/settings", response_model=AlertSettings)
async def alerts_settings_put(body: AlertSettings):
    return await save_alert_settings(body.model_dump())


@app.get("/api/alerts/log")
async def alerts_log(limit: int = Query(50, ge=1, le=200)):
    return await get_alert_log(limit)


@app.post("/api/alerts/test")
async def alerts_test():
    return await send_test_alert()


@app.post("/api/alerts/dispatch-pending")
async def alerts_dispatch_pending(limit: int = Query(20, ge=1, le=100)):
    """Re-send alerts for the most recent signal changes (manual)."""
    changes = await get_signal_changes(limit)
    # normalize keys to dispatcher shape
    normalized = [
        {
            "symbol": c["symbol"],
            "name": c["name"],
            "asset_class": c["asset_class"],
            "previous_action": c["previous_action"],
            "new_action": c["new_action"],
            "previous_confidence": c["previous_confidence"],
            "new_confidence": c["new_confidence"],
            "cycle_source": c["cycle_source"],
            "phase": c["phase"],
            "price": c["price"],
            "created_at": c["created_at"],
        }
        for c in changes
    ]
    return await dispatch_signal_changes(normalized)


# --- WWW (SPA) — one URL for phone / desktop ---

if STATIC_DIR.is_dir():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def spa_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Never steal API routes (registered above); this catches client routes.
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")

