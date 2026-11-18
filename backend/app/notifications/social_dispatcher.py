"""Queue + optionally publish news posts to X / LinkedIn."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.log_redact import scrub_text
from app.news.public_urls import live_domain_ready, public_site_base
from app.models.schemas import MacroNewsItem
from app.news import social_db
from app.news.image_agent import image_file_path
from app.news.social_composer import compose_for_platforms, compose_x
from app.news.google_news_urls import ensure_clickable_url, is_google_news_url
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
        "auto_max_per_day": int(getattr(settings, "social_auto_max_per_day", 2) or 2),
        "domain_ready": live_domain_ready(),
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


class DryRunPublicationBlocked(RuntimeError):
    """Real publishing while CYCLICAL_SOCIAL_DRY_RUN is on. Nothing bypasses it."""


class PublishRateLimited(RuntimeError):
    """Manual and automatic posts share the hourly cap."""


async def _publish_live(
    platform: str,
    body: str,
    *,
    source_name: str = "",
    source_url: str = "",
) -> dict:
    if settings.social_dry_run:
        raise DryRunPublicationBlocked(
            "Publikacja zablokowana: tryb próbny (DRY-RUN). "
            "Ustaw CYCLICAL_SOCIAL_DRY_RUN=false, aby wysłać post."
        )
    if platform == "x" and not live_domain_ready():
        logger.info("czeka na domenę")
        raise DryRunPublicationBlocked("czeka na domenę")
    if platform == "x":
        return await post_to_x(body, source_name=source_name, source_url=source_url)
    if platform == "linkedin":
        return await post_to_linkedin(body)
    raise RuntimeError(f"Unknown platform {platform}")


async def publish_post(post_id: int, *, force: bool = False) -> dict:
    """Publish a stored post.

    Dry-run callers (queue, scheduler, bots) pass force=False and only flip the
    row to status dry_run. force=True is the manual button: it never reaches X
    while dry-run is on — the API answers 409.
    """
    post = await social_db.get_post(post_id)
    if not post:
        raise ValueError("Post not found")
    if post["status"] == "posted":
        return post

    if settings.social_dry_run and not force:
        await social_db.update_post_status(post_id, status="dry_run", error=None)
        return {**(await social_db.get_post(post_id) or post), "dry_run": True}

    if settings.social_dry_run:
        raise DryRunPublicationBlocked(
            "Publikacja zablokowana: tryb próbny (DRY-RUN). "
            "Ustaw CYCLICAL_SOCIAL_DRY_RUN=false, aby wysłać post."
        )

    source_name = post.get("source_name") or ""
    source_url = post.get("url") or ""
    try:
        assert_post_has_source(post.get("body") or "", source_name, source_url)
    except RuntimeError as exc:
        await social_db.update_post_status(post_id, status=post["status"], error=str(exc)[:500])
        raise

    platform = post["platform"]
    if not is_whitelisted(source_name, source_url):
        raise RuntimeError("poza białą listą źródeł")
    now_utc = datetime.now(timezone.utc)
    posted_hour = await social_db.count_posted_since(platform, (now_utc - timedelta(hours=1)).isoformat())
    max_per_hour = int(getattr(settings, "social_auto_max_per_hour", 2) or 2)
    if posted_hour >= max_per_hour:
        raise PublishRateLimited(f"limit {max_per_hour} postów na godzinę")

    if platform == "x" and not x_configured():
        await social_db.update_post_status(post_id, status="failed", error="X credentials missing")
        raise RuntimeError("X credentials missing")
    if platform == "linkedin" and not linkedin_configured():
        await social_db.update_post_status(post_id, status="failed", error="LinkedIn credentials missing")
        raise RuntimeError("LinkedIn credentials missing")

    if platform == "x" and not live_domain_ready():
        logger.info("czeka na domenę")
        raise DryRunPublicationBlocked("czeka na domenę")

    if platform == "x":
        decision = await _manual_x_decision(post)
        if decision.action != "publish":
            await social_db.insert_decision(
                news_id=str(post.get("news_id") or ""),
                title=str(post.get("title") or ""),
                source=str(post.get("source_name") or ""),
                action="odrzucono",
                reason=decision.reason,
                score=decision.score,
            )
            raise RuntimeError(decision.reason)

    try:
        result = await _publish_live(
            platform,
            post["body"],
            source_name=source_name,
            source_url=source_url,
        )
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
        safe = str(scrub_text(str(exc)))[:500]
        await social_db.update_post_status(post_id, status="failed", error=safe)
        logger.warning("Social publish failed id=%s: %s", post_id, safe)
        raise


def _as_utc(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


async def _manual_x_decision(post: dict) -> AutoDecision:
    """Same hottest-topic gate as auto-X, scored from the stored post."""
    now = datetime.now(timezone.utc)
    posted_day = await social_db.count_posted_since("x", (now - timedelta(hours=24)).isoformat())
    posted_hour = await social_db.count_posted_since("x", (now - timedelta(hours=1)).isoformat())
    topics = await social_db.posted_topic_keys("x", (now - timedelta(hours=24)).isoformat())
    title = str(post.get("title") or "")
    return evaluate_auto(
        source=post.get("source_name"),
        url=post.get("url"),
        title=title,
        summary=title,
        impact="medium",
        category="global",
        published_at=_as_utc(post.get("created_at")),
        now=now,
        confirming_sources=1,
        posted_last_day=posted_day,
        recent_topics=topics,
        min_score=int(getattr(settings, "social_auto_min_score", 70) or 70),
        max_per_day=int(getattr(settings, "social_auto_max_per_day", 2) or 2),
        posted_last_hour=posted_hour,
        max_per_hour=int(getattr(settings, "social_auto_max_per_hour", 2) or 2),
    )


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
    from app.net_guard import public_url_ok
    import httpx

    url = (getattr(settings, "social_webhook_url", None) or "").strip()
    if not url:
        return
    if not url.lower().startswith("https://") or not public_url_ok(url):
        logger.warning("Social webhook blocked")
        return
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            await client.post(url, json={"event": "x_published", "post": record})
    except Exception as exc:
        logger.warning("Social webhook failed: %s", type(exc).__name__)


async def run_auto_x(items: list[MacroNewsItem], locale: str = "pl") -> dict:
    """Publish at most two posts a day. Logs every whitelist decision."""
    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(hours=24)).isoformat()
    hour_ago = (now - timedelta(hours=1)).isoformat()
    posted = await social_db.count_posted_since("x", day_ago)
    posted_hour = await social_db.count_posted_since("x", hour_ago)
    topics = await social_db.posted_topic_keys("x", day_ago)
    min_score = int(getattr(settings, "social_auto_min_score", 70) or 70)
    max_per_day = int(getattr(settings, "social_auto_max_per_day", 2) or 2)
    max_per_hour = int(getattr(settings, "social_auto_max_per_hour", 2) or 2)

    pool: list[MacroNewsItem] = []
    outside = 0
    for item in items:
        url = item.url or ""
        if is_google_news_url(url):
            resolved = await ensure_clickable_url(url, item.title)
            if resolved and not is_google_news_url(resolved) and "news.google.com/" not in resolved:
                item = item.model_copy(update={"url": resolved})
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
            posted_last_day=posted,
            recent_topics=topics,
            min_score=min_score,
            max_per_day=max_per_day,
            posted_last_hour=posted_hour,
            max_per_hour=max_per_hour,
        )
        ranked.append((decision, item))
    ranked.sort(key=lambda pair: pair[0].score, reverse=True)

    published = 0
    published_hour = 0
    for decision, item in ranked:
        final = decision
        if final.action == "publish" and settings.social_dry_run:
            final = AutoDecision("reject", "tryb próbny (DRY-RUN)", final.score, final.topic)
        if final.action == "publish" and not x_configured():
            final = AutoDecision("reject", "brak tokenów X", final.score, final.topic)
        if final.action == "publish" and not live_domain_ready():
            logger.info("czeka na domenę")
            final = AutoDecision("reject", "czeka na domenę", final.score, final.topic)
        if final.action == "publish" and posted_hour + published_hour >= max_per_hour:
            final = AutoDecision("reject", f"limit {max_per_hour} postów na godzinę", final.score, final.topic)
        if final.action == "publish" and posted + published >= max_per_day:
            final = AutoDecision("reject", f"limit {max_per_day} postów na dobę", final.score, final.topic)
        if final.action == "publish" and final.topic and final.topic in topics:
            final = AutoDecision("reject", "duplikat tematu", final.score, final.topic)
        if final.action == "publish":
            content = social_db.content_key("x", item.id, item.url)
            if await social_db.has_content_key(content):
                final = AutoDecision("reject", "duplikat tematu", final.score, final.topic)
        if final.action == "publish":
            composed = compose_x(item, locale)
            try:
                assert_post_has_source(composed.body, item.source, item.url)
                result = await _publish_live(
                    "x",
                    composed.body,
                    source_name=item.source or "",
                    source_url=item.url or "",
                )
            except Exception as exc:
                final = AutoDecision("reject", str(exc)[:180], final.score, final.topic)
            else:
                posted_at = datetime.now(timezone.utc).isoformat()
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
                published_hour += 1
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


async def _queue_live_guard(item: MacroNewsItem, body: str, platform: str) -> str | None:
    """None when this queued post may go live. Same rules as run_auto_x."""
    if platform != "x" or not settings.social_auto_post:
        return "auto wyłączone"
    if not is_whitelisted(item.source, item.url):
        return "poza białą listą źródeł"
    if not live_domain_ready():
        logger.info("czeka na domenę")
        return "czeka na domenę"
    now = datetime.now(timezone.utc)
    posted_day = await social_db.count_posted_since("x", (now - timedelta(hours=24)).isoformat())
    posted_hour = await social_db.count_posted_since("x", (now - timedelta(hours=1)).isoformat())
    topics = await social_db.posted_topic_keys("x", (now - timedelta(hours=24)).isoformat())
    decision = evaluate_auto(
        source=item.source,
        url=item.url,
        title=item.title,
        summary=item.summary,
        impact=item.impact,
        category=item.category,
        published_at=item.published_at,
        now=now,
        confirming_sources=1,
        posted_last_day=posted_day,
        recent_topics=topics,
        min_score=int(getattr(settings, "social_auto_min_score", 70) or 70),
        max_per_day=int(getattr(settings, "social_auto_max_per_day", 2) or 2),
        posted_last_hour=posted_hour,
        max_per_hour=int(getattr(settings, "social_auto_max_per_hour", 2) or 2),
    )
    if decision.action != "publish":
        return decision.reason
    try:
        assert_post_has_source(body, item.source, item.url)
    except RuntimeError as exc:
        return str(exc)
    return None


async def queue_social_from_news_items(items: list[MacroNewsItem], locale: str = "pl") -> dict:
    """Compose + store posts. Auto-send only when the switch is on and rules pass."""
    if not settings.social_enabled:
        return {"queued": 0, "skipped": "disabled"}

    auto = {"published": 0}
    if settings.social_auto_post and "x" in social_platforms():
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

            guard = await _queue_live_guard(item, composed.body, composed.platform)
            should_live = (
                not settings.social_dry_run
                and guard is None
                and await _cooldown_ok(composed.platform)
                and (
                    (composed.platform == "x" and x_configured())
                    or (composed.platform == "linkedin" and linkedin_configured())
                )
            )

            if should_live:
                try:
                    if composed.platform == "x":
                        assert_post_has_source(composed.body, item.source, item.url)
                    result = await _publish_live(
                        composed.platform,
                        composed.body,
                        source_name=item.source or "",
                        source_url=item.url or "",
                    )
                    status = "posted"
                    external_id = result.get("external_id")
                    posted_at = datetime.now(timezone.utc).isoformat()
                    posted += 1
                    await social_db.insert_decision(
                        news_id=item.id,
                        title=item.title,
                        source=item.source or "",
                        action="opublikowano",
                        reason="próg spełniony",
                        score=int(getattr(settings, "social_auto_min_score", 70) or 70),
                    )
                except Exception as exc:
                    status = "failed"
                    error = str(exc)[:500]
                    logger.warning("Auto social failed %s: %s", composed.platform, exc)
            elif guard:
                logger.info("Social skip %s: %s", composed.platform, guard)
                if guard != "auto wyłączone":
                    await social_db.insert_decision(
                        news_id=item.id,
                        title=item.title,
                        source=item.source or "",
                        action="odrzucono",
                        reason=guard,
                        score=0,
                    )
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
