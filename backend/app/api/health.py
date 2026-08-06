from fastapi import APIRouter

from app.config import settings
from app.scheduler.jobs import is_running
from app.scanners.opportunity_scanner import scanner
from app.api.spa import STATIC_DIR

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    return {
        "status": "ok",
        "scanner_running": is_running(),
        "live_mode": scanner.live_mode,
        "price_poll_seconds": settings.price_poll_interval_seconds,
        "www": STATIC_DIR.exists(),
    }
