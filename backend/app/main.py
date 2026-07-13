import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.database import (
    get_alert_settings,
    get_notification_log,
    get_push_subscriptions,
    get_recent_opportunities,
    init_db,
    save_push_subscription,
    update_alert_settings,
)
from app.paper.paper_db import init_paper_db
from app.paper.portfolio_agent import sync_after_trade, sync_on_startup
from app.data.chart_data import CHART_PRESETS, fetch_chart
from app.models.schemas import (
    AlertSettings,
    ChartResponse,
    DashboardResponse,
    MarketSummary,
    NotificationStatus,
    PaperOrderRequest,
    PaperPortfolio,
    PaperTradeView,
    PushSubscriptionRequest,
    RegionalCycleSnapshot,
    TwilioConfigRequest,
)
from app.notifications.credentials import save_twilio_credentials, twilio_is_configured
from app.notifications.ntfy import send_ntfy_test
from app.notifications.sms_test import send_sms_test
from app.notifications.alert_engine import alert_engine
from app.notifications.push import get_vapid_public_key, vapid_configured
from app.notifications.vapid_setup import ensure_vapid_keys
from app.realtime.broadcaster import broadcaster
from app.scheduler.jobs import is_running, scheduled_full_scan, start_scheduler, stop_scheduler
from app.paper.executor import PaperTradeError, max_buy_quantity, place_order
from app.paper.paper_db import reset_account
from app.paper.portfolio_service import build_portfolio
from app.scanners.opportunity_scanner import scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_paper_db()
    await sync_on_startup()
    ensure_vapid_keys()
    start_scheduler()

    async def _initial_scan() -> None:
        try:
            await scheduled_full_scan()
            if scanner.market_assessments:
                alert_engine.reset(scanner.market_assessments)
        except Exception as exc:
            logger.warning("Initial scan failed (will retry on schedule): %s", exc)

    asyncio.create_task(_initial_scan())
    yield
    stop_scheduler()


app = FastAPI(
    title="Cyclical Trader",
    description="Aplikacja tradingowa — cykle rynkowe, śledzenie live, powiadomienia push/SMS",
    version="1.3.0",
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
    return {
        "status": "ok",
        "scanner_running": is_running(),
        "live_mode": scanner.live_mode,
        "price_poll_seconds": settings.price_poll_interval_seconds,
        "www": STATIC_DIR.exists(),
    }


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
        last_price_tick_at=scanner.last_price_tick_at,
        live_mode=scanner.live_mode,
        scanner_running=is_running(),
        scan_in_progress=scanner.scan_in_progress,
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
async def trigger_scan(background_tasks: BackgroundTasks):
    if scanner.scan_in_progress:
        return {
            "scanned": False,
            "background": True,
            "already_running": True,
            "opportunities_count": len(scanner.opportunities),
        }

    async def _run_scan() -> None:
        try:
            opportunities = await scanner.scan()
            from app.db.database import save_opportunities

            await save_opportunities(opportunities)
        except Exception as exc:
            logger.exception("Background scan failed: %s", exc)

    background_tasks.add_task(_run_scan)
    return {
        "scanned": True,
        "background": True,
        "already_running": False,
        "opportunities_count": len(scanner.opportunities),
    }


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


@app.get("/api/notifications/status", response_model=NotificationStatus)
async def notification_status():
    settings_data = await get_alert_settings()
    subs = await get_push_subscriptions()
    topic = settings_data.get("ntfy_topic", "")
    return NotificationStatus(
        push_configured=vapid_configured(),
        sms_configured=twilio_is_configured(),
        ntfy_configured=bool(topic),
        ntfy_subscribe_url=f"https://ntfy.sh/{topic}" if topic else "",
        ntfy_app_url=f"ntfy://{topic}" if topic else "",
        vapid_public_key=get_vapid_public_key(),
        push_subscriptions=len(subs),
        settings=AlertSettings(**settings_data),
    )


@app.get("/api/notifications/settings", response_model=AlertSettings)
async def get_notifications_settings():
    return AlertSettings(**await get_alert_settings())


@app.put("/api/notifications/settings", response_model=AlertSettings)
async def put_notifications_settings(body: AlertSettings):
    updated = await update_alert_settings(body.model_dump())
    return AlertSettings(**updated)


@app.post("/api/notifications/push/subscribe")
async def push_subscribe(body: PushSubscriptionRequest):
    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")
    if not body.endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Niepełna subskrypcja push")
    await save_push_subscription(body.endpoint, p256dh, auth)
    return {"subscribed": True}


@app.get("/api/notifications/log")
async def notification_log(limit: int = 30):
    return await get_notification_log(limit)


@app.post("/api/notifications/twilio")
async def save_twilio_config(body: TwilioConfigRequest):
    if not body.account_sid.startswith("AC") or len(body.auth_token) < 10:
        raise HTTPException(status_code=400, detail="Nieprawidłowe dane Twilio")
    if not body.from_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Numer nadawcy w formacie E.164 (+...)")
    save_twilio_credentials(body.account_sid, body.auth_token, body.from_number)
    return {"saved": True, "sms_configured": True}


@app.post("/api/notifications/test")
async def test_notifications():
    settings_data = await get_alert_settings()
    topic = settings_data.get("ntfy_topic", "")
    results: dict[str, object] = {}

    if settings_data.get("ntfy_enabled") and topic:
        ok = await send_ntfy_test(topic)
        results["ntfy"] = {"ok": ok, "topic": topic, "url": f"https://ntfy.sh/{topic}"}

    sms_ok, sms_msg = await send_sms_test()
    results["sms"] = {"ok": sms_ok, "message": sms_msg}

    return results


@app.get("/api/paper/portfolio", response_model=PaperPortfolio)
async def paper_portfolio():
    if not scanner.quotes:
        await scanner.scan()
    data = await build_portfolio()
    return PaperPortfolio(**data)


@app.get("/api/paper/max-buy/{symbol:path}")
async def paper_max_buy(symbol: str):
    if not scanner.quotes:
        await scanner.scan()
    qty = await max_buy_quantity(symbol)
    return {"symbol": symbol, "max_quantity": qty}


@app.get("/api/paper/trades/{symbol:path}", response_model=list[PaperTradeView])
async def paper_trades_for_symbol(symbol: str, limit: int = 200):
    from app.paper.paper_db import get_trades_for_symbol

    rows = await get_trades_for_symbol(symbol, limit=limit)
    return [PaperTradeView(**r) for r in rows]


@app.post("/api/paper/order")
async def paper_order(body: PaperOrderRequest):
    if not scanner.quotes:
        await scanner.scan()
    try:
        trade = await place_order(
            body.symbol, body.side, quantity=body.quantity, amount_pln=body.amount_pln
        )
        portfolio = await build_portfolio()
        return {"trade": trade, "portfolio": portfolio}
    except PaperTradeError as exc:
        raise HTTPException(status_code=400, detail={"message": exc.message, "code": exc.code})


@app.post("/api/paper/reset")
async def paper_reset():
    await reset_account()
    await sync_after_trade()
    return await build_portfolio()


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await broadcaster.connect_ws(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.disconnect_ws(ws)


@app.get("/api/live/stream")
async def live_stream():
    async def event_generator():
        queue = broadcaster.connect_sse()
        try:
            yield f"data: {json.dumps({'type': 'connected', 'live_mode': scanner.live_mode})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            broadcaster.disconnect_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
