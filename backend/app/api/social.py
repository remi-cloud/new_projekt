"""Social desk API — dry-run queue + manual publish."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.news import social_db
from app.notifications.social_dispatcher import (
    DryRunPublicationBlocked,
    public_x_record,
    publish_post,
    social_platforms,
    social_status,
)

router = APIRouter(tags=["social"])


def _require_internal(request: Request) -> None:
    expected = (settings.internal_api_token or "").strip()
    supplied = request.headers.get("x-internal-token", "")
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Kolejka i dziennik są tylko wewnętrzne.")


@router.get("/api/social/status")
async def get_social_status():
    return social_status()


@router.get("/api/social/posts")
async def get_social_posts(request: Request, limit: int = 40):
    _require_internal(request)
    platforms = social_platforms()
    posts = await social_db.list_posts(limit=limit)
    posts = [post for post in posts if post.get("platform") in platforms]
    return {"count": len(posts), "posts": posts, "status": social_status()}


@router.get("/api/social/published")
async def published_posts(limit: int = 30):
    """Public read-only list of posts that were actually sent to X."""
    rows = await social_db.list_published(limit)
    return {"posts": [public_x_record(row) for row in rows]}


@router.get("/api/social/decisions")
async def social_decisions(request: Request, limit: int = 40):
    """Why the automatic publisher sent or skipped a story. Internal only."""
    _require_internal(request)
    return {"decisions": await social_db.list_decisions(limit)}


@router.post("/api/social/posts/{post_id}/publish")
async def publish_social_post(post_id: int):
    """Publish a queued post. Refused with 409 while DRY-RUN is on."""
    if social_status()["dry_run"]:
        raise HTTPException(
            status_code=409,
            detail=(
                "Publikacja zablokowana: tryb próbny (DRY-RUN). "
                "Ustaw CYCLICAL_SOCIAL_DRY_RUN=false, aby wysłać post."
            ),
        )
    try:
        post = await publish_post(post_id, force=False)
    except DryRunPublicationBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError:
        raise HTTPException(status_code=404, detail="Post not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:300]) from None
    return {"ok": True, "post": post}
