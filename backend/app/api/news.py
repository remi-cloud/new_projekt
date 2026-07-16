import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.news.image_agent import has_image as news_has_image, image_file_path, purge_legacy_images
from app.news.macro_news import (
    get_macro_calendar_month,
    get_macro_news,
    patch_cached_image,
    refresh_macro_news,
    schedule_news_images,
)
from app.news.news_alerts import news_alert_engine
from app.notifications.news_dispatcher import dispatch_news_alerts
from app.models.schemas import MacroCalendarMonthResponse, MacroNewsFeed
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)
router = APIRouter(tags=["news"])


async def on_news_image_ready(news_id: str, image_url: str) -> None:
    await patch_cached_image(news_id, image_url)
    await broadcaster.publish("macro_news_image", {"news_id": news_id, "image_url": image_url})


async def kick_news_images(items) -> None:
    """Generate hero images in batches until feed is covered or batch limit exhausted."""
    remaining = list(items)
    for _ in range(8):
        if not remaining:
            break
        pending_before = sum(1 for i in remaining if not news_has_image(i.id))
        if pending_before == 0:
            break
        await schedule_news_images(remaining, on_ready=on_news_image_ready)
        remaining = [i for i in remaining if not news_has_image(i.id)]
        if pending_before == len(remaining):
            break
        await asyncio.sleep(0.3)


async def initial_news() -> None:
    try:
        purge_legacy_images()
        feed, all_items = await refresh_macro_news()
        news_alert_engine.reset(all_items)
        asyncio.create_task(kick_news_images(feed.items))
    except Exception as exc:
        logger.warning("Initial macro news fetch failed: %s", exc)


@router.get("/api/news/calendar", response_model=MacroCalendarMonthResponse)
async def macro_calendar_month(year: int | None = None, month: int | None = None, lang: str | None = None):
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="Month must be 1–12")
    return await get_macro_calendar_month(y, m, locale=lang)


@router.get("/api/news/macro", response_model=MacroNewsFeed)
async def macro_news(category: str | None = None, limit: int = 50, lang: str | None = None):
    if category and category not in ("all", "fed", "usa", "macro", "global", "musk"):
        raise HTTPException(status_code=400, detail="Category: all, fed, usa, macro, global, musk")
    return await get_macro_news(category=category, limit=min(limit, 100), locale=lang)


@router.post("/api/news/macro/refresh", response_model=MacroNewsFeed)
async def macro_news_refresh(lang: str | None = None):
    feed, all_items = await refresh_macro_news()
    events = news_alert_engine.diff(all_items)
    if events:
        await dispatch_news_alerts(events)
    asyncio.create_task(kick_news_images(feed.items))
    return await get_macro_news(limit=100, locale=lang)


@router.get("/api/news/images/{news_id}")
async def news_image(news_id: str):
    if not news_id or ".." in news_id or "/" in news_id:
        raise HTTPException(status_code=400, detail="Invalid news id")
    path = image_file_path(news_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/webp", filename=f"{news_id}.webp")
