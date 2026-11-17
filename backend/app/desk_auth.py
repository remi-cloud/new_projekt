"""Desk token for state-changing requests. Empty token means closed."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

router = APIRouter(tags=["desk"])

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_LOGIN_PATH = "/api/desk/login"


def tokens_match(supplied: str, expected: str) -> bool:
    """Compare digests so a shorter guess does not exit early."""
    left = hashlib.sha256(supplied.encode()).digest()
    right = hashlib.sha256(expected.encode()).digest()
    return hmac.compare_digest(left, right)


def desk_configured() -> bool:
    return bool((settings.desk_token or "").strip())


class DeskLoginBody(BaseModel):
    token: str = ""


@router.get("/api/desk/status")
async def desk_status():
    return {"configured": desk_configured()}


@router.post("/api/desk/login")
async def desk_login(body: DeskLoginBody):
    expected = (settings.desk_token or "").strip()
    if not expected:
        raise HTTPException(status_code=403, detail="Biurko zamknięte. Ustaw CYCLICAL_DESK_TOKEN.")
    if not tokens_match(body.token or "", expected):
        raise HTTPException(status_code=401, detail="Zły token biurka.")
    return {"ok": True}


class DeskAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS or request.url.path == _LOGIN_PATH:
            return await call_next(request)
        expected = (settings.desk_token or "").strip()
        if not expected:
            return JSONResponse(
                status_code=403,
                content={"detail": "Biurko zamknięte. Ustaw CYCLICAL_DESK_TOKEN."},
            )
        supplied = request.headers.get("x-desk-token", "")
        if not tokens_match(supplied, expected):
            return JSONResponse(status_code=401, content={"detail": "Zły token biurka."})
        return await call_next(request)
