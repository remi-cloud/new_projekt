"""Queue + optionally publish news posts to X / LinkedIn."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.news.public_urls import public_site_base
from app.models.schemas import MacroNewsItem
from app.news import social_db
from app.news.image_agent import image_file_path
from app.news.social_composer import compose_for_platforms, compose_x
from app.news.x_auto import (
    AutoDecision,
    assert_post_has_source,
    evaluate_auto,
    is_whitelisted,
    topic_key,
    x_status_url,
)
from app.notifications.social_clients import (
    linkedin_configured,
    post_to_linkedin,
    post_to_x,
    x_configured,
)

logger = logging.getLogger(__name__)


def social_platforms() -> list[str]:
    """Platforms the news desk may queue. Default is X only."""
    allowed = {"x", "linkedin"}
    raw = (getattr(settings, "social_platforms", None) or "x").split(",")
    picked = [part.strip().lower() for part in raw if part.strip().lower() in allowed]
    return picked or ["x"]


def social_status() -> dict:
    return {
        "enabled": bool(settings.social_enabled),
        "dry_run": bool(settings.social_dry_run),
        "auto_post": bool(settings.social_auto_post),
        "platforms": social_platforms(),
        "auto_min_score": int(getattr(settings, "social_auto_min_score", 70) or 70),
        "auto_max_per_hour": int(getattr(settings, "social_auto_max_per_hour", 2) or 2),
        "cooldown_minutes": settings.social_cooldown_minutes,
        "max_per_cycle": settings.social_max_per_cycle,
        "public_base_url": public_site_base() or None,
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

    try:
        assert_post_has_source(post.get("body") or "", post.get("source_name"), post.get("url"))
    except RuntimeError as exc:
        await social_db.update_post_status(post_id, status=post["status"], error=str(exc)[:500])
        raise

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
        saved = await social_db.get_post(post_id) or post
        await _notify_webhook(public_x_record(saved))
        return saved
    except Exception as exc:
        await social_db.update_post_status(post_id, status="failed", error=str(exc)[:500])
        logger.warning("Social publish failed id=%s: %s", post_id, exc)
        raise


def public_x_record(post: dict) -> dict:
    """Read-only view of a published X post. No tokens, no webhook URL."""
    external_id = post.get("external_id") or None
    return {
        "id": post.get("id"),
        "x_post_id": external_id,
        "x_url": x_status_url(external_id),
        "body": post.get("body") or "",
        "source_name": post.get("source_name") or "",
        "source_url": post.get("url") or "",
        "published_at": post.get("posted_at"),
    }


async def _notify_webhook(record: dict) -> None:
    url = (getattr(settings, "social_webhook_url", None) or "").strip()
    if not url:
        return
    import httpx

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(url, json={"event": "x_published", "post": record})
    except Exception as exc:
        logger.warning("Social webhook failed: %s", type(exc).__name__)


async def run_auto_x(items: list[MacroNewsItem], locale: str = "pl") -> dict:
    """Publish at most the hourly allowance. Logs every whitelist decision."""
    now = datetime.now(timezone.utc)
    hour_ago = (now - timedelta(hours=1)).isoformat()
    day_ago = (now - timedelta(hours=24)).isoformat()
    posted = await social_db.count_posted_since("x", hour_ago)
    topics = await social_db.posted_topic_keys("x", day_ago)
    min_score = int(getattr(settings, "social_auto_min_score", 70) or 70)
    max_per_hour = int(getattr(settings, "social_auto_max_per_hour", 2) or 2)

    pool: list[MacroNewsItem] = []
    outside = 0
    for item in items:
        if is_whitelisted(item.source, item.url):
            pool.append(item)
        else:
            outside += 1
    if outside and not pool:
        await social_db.insert_decision(
            news_id="",
            title="",
            source="",
            action="odrzucono",
            reason=f"poza białą listą ({outside})",
            score=0,
        )

    groups: dict[str, set[str]] = {}
    for item in pool:
        key = topic_key(item.title)
        groups.setdefault(key, set()).add((item.source or "").strip().lower())

    ranked: list[tuple[AutoDecision, MacroNewsItem]] = []
    for item in pool:
        key = topic_key(item.title)
        decision = evaluate_auto(
            source=item.source,
            url=item.url,
            title=item.title,
            summary=item.summary,
            impact=item.impact,
            category=item.category,
            published_at=item.published_at,
            now=now,
            confirming_sources=max(1, len(groups.get(key) or ())),
            posted_last_hour=posted,
            recent_topics=topics,
            min_score=min_score,
            max_per_hour=max_per_hour,
        )
        ranked.append((decision, item))
    ranked.sort(key=lambda pair: pair[0].score, reverse=True)

    published = 0
    for decision, item in ranked:
        final = decision
        if final.action == "publish" and posted + published >= max_per_hour:
            final = AutoDecision("reject", f"limit {max_per_hour} postów na godzinę", final.score, final.topic)
        if final.action == "publish" and not x_configured():
            final = AutoDecision("reject", "brak tokenów X", final.score, final.topic)
        if final.action == "publish":
            composed = compose_x(item, locale)
            try:
                assert_post_has_source(composed.body, item.source, item.url)
                result = await _publish_live("x", composed.body)
            except Exception as exc:
                final = AutoDecision("reject", str(exc)[:180], final.score, final.topic)
            else:
                posted_at = datetime.now(timezone.utc).isoformat()
                if not await social_db.has_content_key(social_db.content_key("x", item.id, item.url)):
                    await social_db.insert_post(
                        platform="x",
                        news_id=item.id,
                        url=item.url,
                        title=composed.title,
                        body=composed.body,
                        media_path=None,
                        status="posted",
                        external_id=result.get("external_id"),
                        posted_at=posted_at,
                        source_name=item.source,
                    )
                published += 1
                topics.add(final.topic)
                await _notify_webhook(
                    public_x_record(
                        {
                            "id": None,
                            "external_id": result.get("external_id"),
                            "body": composed.body,
                            "source_name": item.source,
                            "url": item.url,
                            "posted_at": posted_at,
                        }
                    )
                )
        await social_db.insert_decision(
            news_id=item.id,
            title=item.title,
            source=item.source or "",
            action="opublikowano" if final.action == "publish" else "odrzucono",
            reason=final.reason,
            score=final.score,
        )
    return {"considered": len(pool), "published": published, "outside_whitelist": outside}


async def queue_social_from_news_items(items: list[MacroNewsItem], locale: str = "pl") -> dict:
    """Compose + store posts. Auto-send only when the switch is on and rules pass."""
    if not settings.social_enabled:
        return {"queued": 0, "skipped": "disabled"}

    auto = {"published": 0}
    if settings.social_auto_post and not settings.social_dry_run and "x" in social_platforms():
        auto = await run_auto_x(items, locale)

    selected = _select_items(items)
    queued = 0
    posted = 0
    skipped = 0

    for item in selected:
        media = None
        path = image_file_path(item.id)
        if path.is_file():
            media = str(path)

        allowed = set(social_platforms())
        for composed in compose_for_platforms(item, locale=locale):
            if composed.platform not in allowed:
                continue
            key = social_db.content_key(composed.platform, item.id, item.url)
            if await social_db.has_content_key(key):
                skipped += 1
                continue

            status = "dry_run" if settings.social_dry_run else "ready"
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
                source_name=item.source,
            )
            queued += 1

    return {
        "queued": queued,
        "posted": posted + int(auto.get("published") or 0),
        "skipped": skipped,
        "selected": len(selected),
        "auto": auto,
    }
