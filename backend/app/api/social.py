"""Social desk API — dry-run queue + manual publish."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.news import social_db
from app.notifications.social_dispatcher import publish_post, social_status

router = APIRouter(tags=["social"])


@router.get("/api/social/status")
async def get_social_status():
    return social_status()


@router.get("/api/social/posts")
async def get_social_posts(limit: int = 40):
    posts = await social_db.list_posts(limit=limit)
    return {"count": len(posts), "posts": posts, "status": social_status()}


@router.post("/api/social/posts/{post_id}/publish")
async def publish_social_post(post_id: int):
    """Force-publish a queued/dry-run post (bypasses dry_run flag once)."""
    try:
        post = await publish_post(post_id, force=True)
    except ValueError:
        raise HTTPException(status_code=404, detail="Post not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:300]) from None
    return {"ok": True, "post": post}
