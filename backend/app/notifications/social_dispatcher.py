"""Queue + optionally publish news posts to X / LinkedIn."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.schemas import MacroNewsItem
from app.news import social_db
from app.news.image_agent import image_file_path
from app.news.social_composer import compose_for_platforms
from app.notifications.social_clients import (
    linkedin_configured,
    post_to_linkedin,
    post_to_x,
    x_configured,
)

logger = logging.getLogger(__name__)


def social_status() -> dict:
    return {
        "enabled": bool(settings.social_enabled),
        "dry_run": bool(settings.social_dry_run),
        "auto_post": bool(settings.social_auto_post),
        "cooldown_minutes": settings.social_cooldown_minutes,
        "max_per_cycle": settings.social_max_per_cycle,
        "public_base_url": settings.public_base_url or None,
        "x_configured": x_configured(),
        "linkedin_configured": linkedin_configured(),
    }


def _select_items(items: list[MacroNewsItem]) -> list[MacroNewsItem]:
    """High-impact fresh or curated — newest first, capped."""
    now = datetime.now(timezone.utc)
    fresh = timedelta(hours=max(1, settings.news_fresh_hours))
    scored: list[MacroNewsItem] = []
    for item in items:
        age = now - item.published_at
        if item.is_curated:
            scored.append(item)
        elif item.impact == "high" and age <= fresh:
            scored.append(item)
    scored.sort(key=lambda i: i.published_at, reverse=True)
    return scored[: max(1, settings.social_max_per_cycle)]


async def _cooldown_ok(platform: str) -> bool:
    last = await social_db.last_posted_at(platform)
    if not last:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last >= timedelta(minutes=settings.social_cooldown_minutes)


async def _publish_live(platform: str, body: str) -> dict:
    if platform == "x":
        return await post_to_x(body)
    if platform == "linkedin":
        return await post_to_linkedin(body)
    raise RuntimeError(f"Unknown platform {platform}")


async def publish_post(post_id: int, *, force: bool = False) -> dict:
    """Publish a stored post. force=True bypasses dry_run (manual UI button)."""
    post = await social_db.get_post(post_id)
    if not post:
        raise ValueError("Post not found")
    if post["status"] == "posted":
        return post

    if settings.social_dry_run and not force:
        await social_db.update_post_status(post_id, status="dry_run", error=None)
        return {**(await social_db.get_post(post_id) or post), "dry_run": True}

    platform = post["platform"]
    if platform == "x" and not x_configured():
        await social_db.update_post_status(post_id, status="failed", error="X credentials missing")
        raise RuntimeError("X credentials missing")
    if platform == "linkedin" and not linkedin_configured():
        await social_db.update_post_status(post_id, status="failed", error="LinkedIn credentials missing")
        raise RuntimeError("LinkedIn credentials missing")

    try:
        result = await _publish_live(platform, post["body"])
        now = datetime.now(timezone.utc).isoformat()
        await social_db.update_post_status(
            post_id,
            status="posted",
            error=None,
            external_id=result.get("external_id"),
            posted_at=now,
        )
        logger.info("Social posted id=%s platform=%s ext=%s", post_id, platform, result.get("external_id"))
    except Exception as exc:
        await social_db.update_post_status(post_id, status="failed", error=str(exc)[:500])
        logger.warning("Social publish failed id=%s: %s", post_id, exc)
        raise

    return await social_db.get_post(post_id) or post


async def queue_social_from_news_items(items: list[MacroNewsItem], locale: str = "pl") -> dict:
    """Compose + store posts; auto-publish only when configured and not dry-run."""
    if not settings.social_enabled:
        return {"queued": 0, "skipped": "disabled"}

    selected = _select_items(items)
    queued = 0
    posted = 0
    skipped = 0

    for item in selected:
        media = None
        path = image_file_path(item.id)
        if path.is_file():
            media = str(path)

        for composed in compose_for_platforms(item, locale=locale):
            key = social_db.content_key(composed.platform, item.id, item.url)
            if await social_db.has_content_key(key):
                skipped += 1
                continue

            status = "dry_run"
            error = None
            external_id = None
            posted_at = None

            should_live = (
                not settings.social_dry_run
                and settings.social_auto_post
                and await _cooldown_ok(composed.platform)
                and (
                    (composed.platform == "x" and x_configured())
                    or (composed.platform == "linkedin" and linkedin_configured())
                )
            )

            if should_live:
                try:
                    result = await _publish_live(composed.platform, composed.body)
                    status = "posted"
                    external_id = result.get("external_id")
                    posted_at = datetime.now(timezone.utc).isoformat()
                    posted += 1
                except Exception as exc:
                    status = "failed"
                    error = str(exc)[:500]
                    logger.warning("Auto social failed %s: %s", composed.platform, exc)
            else:
                logger.info(
                    "Social dry-run/queued platform=%s news=%s chars=%d",
                    composed.platform,
                    item.id,
                    len(composed.body),
                )

            await social_db.insert_post(
                platform=composed.platform,
                news_id=item.id,
                url=item.url,
                title=composed.title,
                body=composed.body,
                media_path=media,
                status=status,
                error=error,
                external_id=external_id,
                posted_at=posted_at,
            )
            queued += 1

    return {"queued": queued, "posted": posted, "skipped": skipped, "selected": len(selected)}
