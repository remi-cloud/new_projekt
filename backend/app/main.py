import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.data.assets import (
    DEFAULT_ASSETS,
    GLOBAL_MARKET_REGIONS,
    REGION_LABELS,
    enrich_asset,
)
from app.data.market_data import build_markets_quotes
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
    BroadcastResponse,
    DashboardResponse,
    EconomicEvent,
    HistoryResponse,
    MarketRegionCount,
    MarketsResponse,
    SuperOpportunitiesResponse,
    WatchlistAddRequest,
    WatchlistToggleRequest,
)
from app.agents import orchestrator
from app.notifications.dispatcher import dispatch_signal_changes, send_test_alert
from app.scheduler.jobs import (
    is_running,
    run_scan_and_alert,
    scheduled_economic_sync,
    scheduled_scan,
    start_scheduler,
    stop_scheduler,
)
from app.scanners.broadcast import build_broadcast
from app.scanners.opportunity_scanner import scanner
from app.scanners.super_opportunities import build_super_opportunities, build_super_opportunity
from app.db.economic_store import count_economic_events, list_economic_events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()

    # Never block WWW startup on market APIs — scan in background.
    async def _initial_scan() -> None:
        try:
            await scheduled_economic_sync()
        except Exception as exc:
            logger.warning("Initial economic sync failed: %s", exc)
        try:
            await scheduled_scan()
        except Exception as exc:
            logger.warning("Initial scan failed (will retry on schedule): %s", exc)

    asyncio.create_task(_initial_scan())
    yield
    stop_scheduler()


app = FastAPI(
    title="Cyclical Trader",
    description="Multi-agent skaner globalny — 6 LONG + 6 SHORT scouts → AI specjaliści → orchestrator.",
    version="2.0.0",
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
    status = orchestrator.roster_status()
    econ_n = 0
    try:
        econ_n = await count_economic_events()
    except Exception:
        pass
    return {
        "status": "ok",
        "scanner_running": is_running(),
        "last_scan_at": scanner.last_scan_at.isoformat() if scanner.last_scan_at else None,
        "opportunities_count": len(scanner.opportunities),
        "agents": status.get("counts"),
        "economic_events": econ_n,
        "quote_sources": ["yahoo", "tradingview", "coingecko"],
        "calendar_source": "faireconomy",
        "version": "2.1.0",
    }


@app.get("/api/singularity")
@app.get("/api/agents")
async def singularity_war_room():
    """Singularity module: scout roster + specialist verdicts + orchestrator."""
    report = orchestrator.agent_report()
    if not report.get("ready") and (not scanner.alpha_model or not scanner.beta_model):
        asyncio.create_task(scanner.scan())
        raise HTTPException(
            status_code=503,
            detail="Singularity skanuje świat — odśwież za chwilę",
        )
    return report


@app.get("/api/singularity/status")
@app.get("/api/agents/status")
async def singularity_status():
    return orchestrator.roster_status()

@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard():
    # Fast path: if cache empty, kick a scan but do not block the HTTP request
    # (tunnel / phone clients time out on long first scans).
    if not scanner.alpha_model or not scanner.beta_model:
        asyncio.create_task(scanner.scan())
        raise HTTPException(
            status_code=503,
            detail="Skanowanie rynku w toku — odśwież za chwilę",
        )
    return DashboardResponse(
        alpha_model=scanner.alpha_model,
        beta_model=scanner.beta_model,
        opportunities=scanner.opportunities,
        monitored_assets=scanner.quotes,
        last_scan_at=scanner.last_scan_at,
        scanner_running=is_running(),
    )


@app.get("/api/markets", response_model=MarketsResponse)
async def markets(region: str | None = Query(None)):
    """
    Full markets catalog with region tags.

    Independent of Model Alpha/Beta scan — always lists global indexes
    (Asia, Russia, Brazil, Europe, EM) even before the first orchestrator run.
    """
    from datetime import datetime, timezone

    watchlist = await get_watchlist(enabled_only=True)
    assets = [
        enrich_asset(
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "asset_class": item["asset_class"],
                "source": item.get("source", "yahoo"),
            }
        )
        for item in watchlist
    ]
    if not assets:
        assets = [enrich_asset(a) for a in DEFAULT_ASSETS]

    all_quotes = await build_markets_quotes(
        assets,
        cached=scanner.quotes or None,
        fetch_missing=True,
    )

    region_order = {
        "asia": 0,
        "russia": 1,
        "americas": 2,
        "europe": 3,
        "mea": 4,
        "world": 5,
        "usa": 6,
        "crypto": 7,
        "bonds": 8,
        "commodities": 9,
        "forex": 10,
    }

    selected = region or "global"
    if selected == "all":
        items = list(all_quotes)
    elif selected == "global":
        items = [q for q in all_quotes if q.region in GLOBAL_MARKET_REGIONS]
    else:
        items = [q for q in all_quotes if q.region == selected]

    items.sort(
        key=lambda q: (region_order.get(q.region, 50), q.region_label, q.name.lower())
    )

    by_region: dict[str, list] = {}
    for q in all_quotes:
        by_region.setdefault(q.region, []).append(q)

    global_items = [q for q in all_quotes if q.region in GLOBAL_MARKET_REGIONS]
    regions = [
        MarketRegionCount(
            id="global",
            label="Rynki globalne",
            count=len(global_items),
            live_count=sum(1 for x in global_items if x.live and x.price > 0),
        )
    ]
    regions.extend(
        MarketRegionCount(
            id=rid,
            label=REGION_LABELS.get(rid, rid),
            count=len(bucket),
            live_count=sum(1 for x in bucket if x.live and x.price > 0),
        )
        for rid, bucket in sorted(
            by_region.items(),
            key=lambda kv: region_order.get(kv[0], 50),
        )
    )

    now = datetime.now(timezone.utc).isoformat()
    return MarketsResponse(
        generated_at=now,
        count=len(items),
        global_count=len(global_items),
        live_count=sum(1 for q in items if q.live and q.price > 0),
        regions=regions,
        items=items,
    )


@app.get("/api/broadcast", response_model=BroadcastResponse)
async def broadcast(force: bool = Query(False)):
    """
    Red TV ticker payload.
    Visible for 2 minutes at the start of every 20-minute wall-clock window.
    Carries best Singularity setup + high-impact economic headlines.
    """
    return await build_broadcast(force_visible=force)


@app.get("/api/economic-calendar", response_model=list[EconomicEvent])
async def economic_calendar(
    hours_back: int = Query(24, ge=0, le=168),
    hours_ahead: int = Query(168, ge=1, le=336),
    min_impact: int = Query(0, ge=0, le=3),
    limit: int = Query(200, ge=1, le=500),
):
    rows = await list_economic_events(
        hours_back=hours_back,
        hours_ahead=hours_ahead,
        min_impact_rank=min_impact,
        limit=limit,
    )
    return [EconomicEvent(**r) for r in rows]


@app.post("/api/economic-calendar/sync")
async def economic_calendar_sync():
    await scheduled_economic_sync()
    return {"synced": True, "count": await count_economic_events()}


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


@app.get("/api/super-opportunities", response_model=SuperOpportunitiesResponse)
async def super_opportunities(min_score: float = Query(0, ge=0, le=100)):
    """Superokazje: cykl + bid/ask + poziomy wejścia/wyjścia + heatmapa liq."""
    if not scanner.alpha_model or not scanner.beta_model:
        asyncio.create_task(scanner.scan())
        raise HTTPException(status_code=503, detail="Skanowanie rynku w toku — odśwież za chwilę")
    return await build_super_opportunities(min_score=min_score)


@app.get("/api/super-opportunities/{symbol}")
async def super_opportunity_detail(symbol: str):
    if not scanner.opportunities:
        if not scanner.alpha_model:
            asyncio.create_task(scanner.scan())
            raise HTTPException(status_code=503, detail="Skanowanie rynku w toku — odśwież za chwilę")
    match = next((o for o in scanner.opportunities if o.symbol.upper() == symbol.upper()), None)
    if not match:
        raise HTTPException(status_code=404, detail="Brak okazji dla symbolu — uruchom skan / dodaj do watchlisty")
    return await build_super_opportunity(match)


@app.get("/api/models/alpha")
async def alpha_model():
    if not scanner.alpha_model:
        asyncio.create_task(scanner.scan())
        raise HTTPException(status_code=503, detail="Skanowanie rynku w toku — odśwież za chwilę")
    return scanner.alpha_model


@app.get("/api/models/beta")
async def beta_model():
    if not scanner.beta_model:
        asyncio.create_task(scanner.scan())
        raise HTTPException(status_code=503, detail="Skanowanie rynku w toku — odśwież za chwilę")
    return scanner.beta_model


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


@app.get("/status", response_class=HTMLResponse)
async def status_page():
    """No-JS status page — proves WWW works even if React fails to load."""
    ready = bool(scanner.alpha_model and scanner.beta_model)
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Cyclical Trader — status</title>
<style>body{{font-family:system-ui,sans-serif;background:#121a17;color:#eef3ef;padding:24px;line-height:1.5}}
a{{color:#2dd4bf}} .ok{{color:#34d399}} .wait{{color:#fbbf24}}</style></head>
<body>
<h1>Cyclical Trader</h1>
<p class="{'ok' if ready else 'wait'}">API: OK · Skaner: {'gotowy' if ready else 'pierwsze skanowanie…'} · Okazje: {len(scanner.opportunities)}</p>
<p><a href="/">Otwórz aplikację</a> · <a href="/dashboard">Dashboard</a> · <a href="/api/health">/api/health</a></p>
<meta http-equiv="refresh" content="5">
</body></html>"""


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
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi") or full_path == "status":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def missing_static():
        return HTMLResponse(
            "<h1>Brak UI</h1><p>Uruchom <code>./scripts/build-www.sh</code> albo Docker build.</p>"
            "<p><a href='/status'>/status</a> · <a href='/api/health'>/api/health</a></p>",
            status_code=503,
        )

