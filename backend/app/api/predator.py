"""API: Telegram Predator signal desk."""

from fastapi import APIRouter, HTTPException

from app.telegram import predator_db, predator_service

router = APIRouter(prefix="/api/predator", tags=["predator"])


@router.get("/status")
async def predator_status():
    return await predator_service.predator_status()


@router.get("/signals")
async def predator_signals(limit: int = 40):
    await predator_db.init_predator_db()
    rows = await predator_db.list_signals(limit=min(limit, 100))
    return {"count": len(rows), "signals": rows}


@router.post("/poll")
async def predator_poll():
    result = await predator_service.poll_predator_feed(notify=True)
    if result.get("reason") == "no_token":
        raise HTTPException(
            status_code=400,
            detail="Brak CYCLICAL_TELEGRAM_BOT_TOKEN — ustaw darmowy token z @BotFather (docs/TELEGRAM-PREDATOR.md)",
        )
    if result.get("reason") == "disabled":
        raise HTTPException(status_code=400, detail="telegram_predator_enabled=false")
    return result
