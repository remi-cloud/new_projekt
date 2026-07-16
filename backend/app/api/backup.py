from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["backup"])


@router.get("/api/backup/status")
async def backup_status():
    from app.backup import progress_status

    return {
        **progress_status(),
        "ui_auto_refresh_seconds": int(getattr(settings, "ui_auto_refresh_seconds", 20)),
        "auto_backup_enabled": bool(getattr(settings, "auto_backup_enabled", True)),
        "auto_backup_interval_seconds": int(getattr(settings, "auto_backup_interval_seconds", 20)),
    }


@router.post("/api/backup/now")
async def backup_now():
    from app.backup import save_progress

    return save_progress(reason="manual")
