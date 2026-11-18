"""Desk token for state-changing requests. Empty token means closed."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.http_guard import cors_origin_list
from app.public_surface import PUBLIC_WRITE_PATHS

router = APIRouter(tags=["desk"])

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_LOGIN_PATH = "/api/desk/login"
_LOGIN_FAILS: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_LOCK_UNTIL: dict[str, float] = {}
_LOGIN_WINDOW = 900.0
_LOGIN_MAX = 5


def reset_login_guard() -> None:
    _LOGIN_FAILS.clear()
    _LOGIN_LOCK_UNTIL.clear()


def _login_key(request: Request) -> str:
    from app.http_guard import client_key

    return client_key(request)


def login_locked(request: Request) -> bool:
    key = _login_key(request)
    return time.monotonic() < _LOGIN_LOCK_UNTIL.get(key, 0)


def note_login_failure(request: Request) -> None:
    key = _login_key(request)
    now = time.monotonic()
    bucket = _LOGIN_FAILS[key]
    while bucket and now - bucket[0] > _LOGIN_WINDOW:
        bucket.popleft()
    bucket.append(now)
    if len(bucket) >= _LOGIN_MAX:
        _LOGIN_LOCK_UNTIL[key] = now + _LOGIN_WINDOW


def note_login_success(request: Request) -> None:
    key = _login_key(request)
    _LOGIN_FAILS.pop(key, None)
    _LOGIN_LOCK_UNTIL.pop(key, None)


def csrf_ok(request: Request) -> bool:
    """Browser posts must come from our origin. Missing Origin is a non-browser client."""
    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if not origin:
        return True
    allowed = {item.rstrip("/") for item in cors_origin_list()}
    if origin in allowed:
        return True
    host = (request.headers.get("host") or "").split(":")[0]
    if host and origin.split("://", 1)[-1].split(":")[0] == host:
        return True
    return request.headers.get("x-cyclical-request") == "1"


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
async def desk_login(body: DeskLoginBody, request: Request):
    if login_locked(request):
        raise HTTPException(status_code=429, detail="Za dużo prób logowania. Spróbuj za 15 minut.")
    expected = (settings.desk_token or "").strip()
    if not expected:
        raise HTTPException(status_code=403, detail="Biurko zamknięte. Ustaw CYCLICAL_DESK_TOKEN.")
    if not tokens_match(body.token or "", expected):
        note_login_failure(request)
        raise HTTPException(status_code=401, detail="Zły token biurka.")
    note_login_success(request)
    return {"ok": True}


class DeskAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS or request.url.path == _LOGIN_PATH:
            return await call_next(request)
        if request.url.path in PUBLIC_WRITE_PATHS:
            if not csrf_ok(request):
                return JSONResponse(status_code=403, content={"detail": "Żądanie spoza biurka."})
            return await call_next(request)
        expected = (settings.desk_token or "").strip()
        if not expected:
            return JSONResponse(
                status_code=403,
                content={"detail": "Biurko zamknięte. Ustaw CYCLICAL_DESK_TOKEN."},
            )
        supplied = request.headers.get("x-desk-token", "")
        if not supplied:
            return JSONResponse(
                status_code=401,
                content={"detail": "Zaloguj biurko, żeby zmienić stan."},
            )
        if not tokens_match(supplied, expected):
            return JSONResponse(status_code=401, content={"detail": "Zły token biurka."})
        return await call_next(request)
