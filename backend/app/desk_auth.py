"""Desk token for state-changing requests. Empty token means closed.

The browser session is an HttpOnly cookie. The desk token itself is not stored
in the page. API clients may still send X-Desk-Token.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.http_guard import _trusted_proxy, cors_origin_list
from app.public_surface import PUBLIC_WRITE_PATHS

router = APIRouter(tags=["desk"])

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_LOGIN_PATH = "/api/desk/login"
_LOGOUT_PATH = "/api/desk/logout"
COOKIE_NAME = "cyclical_desk_session"
_SESSION_TTL = 12 * 60 * 60
_SESSIONS: dict[str, float] = {}
_LOGIN_FAILS: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_WINDOW = 900.0
_LOGIN_MAX = 5


def reset_login_guard() -> None:
    _LOGIN_FAILS.clear()
    _SESSIONS.clear()


def _login_key(request: Request) -> str:
    from app.http_guard import client_key

    return client_key(request)


def _prune_failures(key: str) -> deque[float]:
    now = time.monotonic()
    bucket = _LOGIN_FAILS[key]
    while bucket and now - bucket[0] > _LOGIN_WINDOW:
        bucket.popleft()
    return bucket


def note_login_failure(request: Request) -> int:
    bucket = _prune_failures(_login_key(request))
    bucket.append(time.monotonic())
    return len(bucket)


def note_login_success(request: Request) -> None:
    _LOGIN_FAILS.pop(_login_key(request), None)


def issue_session() -> str:
    sid = secrets.token_urlsafe(32)
    _SESSIONS[sid] = time.monotonic() + _SESSION_TTL
    return sid


def session_valid(sid: str | None) -> bool:
    if not sid:
        return False
    expiry = _SESSIONS.get(sid)
    if expiry is None or time.monotonic() >= expiry:
        _SESSIONS.pop(sid, None)
        return False
    return True


def drop_session(sid: str | None) -> None:
    if sid:
        _SESSIONS.pop(sid, None)


def request_is_https(request: Request) -> bool:
    """Secure cookies only on HTTPS. Loopback HTTP would drop a Secure cookie."""
    scheme = (request.url.scheme or "").lower()
    peer = request.client.host if request.client else ""
    if _trusted_proxy(peer):
        forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        if forwarded:
            scheme = forwarded
    return scheme == "https"


def _set_session_cookie(response: Response, request: Request, sid: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=sid,
        max_age=_SESSION_TTL,
        httponly=True,
        secure=request_is_https(request),
        samesite="strict",
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=request_is_https(request),
        samesite="strict",
        path="/",
    )


def request_authenticated(request: Request) -> bool:
    expected = (settings.desk_token or "").strip()
    if not expected:
        return False
    supplied = request.headers.get("x-desk-token", "")
    if supplied and tokens_match(supplied, expected):
        return True
    return session_valid(request.cookies.get(COOKIE_NAME))


def require_desk(request: Request) -> None:
    """401/403 for routes the middleware does not cover (GET refresh/force)."""
    expected = (settings.desk_token or "").strip()
    if not expected:
        raise HTTPException(status_code=403, detail="Biurko zamknięte. Ustaw CYCLICAL_DESK_TOKEN.")
    if not request_authenticated(request):
        raise HTTPException(status_code=401, detail="Zaloguj biurko, żeby zmienić stan.")


def csrf_ok(request: Request) -> bool:
    """Browser posts must come from our origin. Missing Origin is a non-browser client."""
    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if not origin:
        return True
    allowed = {item.rstrip("/") for item in cors_origin_list()}
    if origin in allowed:
        return True
    host = (request.headers.get("host") or "").split(":")[0]
    return bool(host) and origin.split("://", 1)[-1].split(":")[0] == host


def supplied_desk_token(request: Request) -> str:
    """Header for API clients. A valid session cookie stands in for the desk token.

    The cookie holds a random session id, not the desk token.
    """
    header = request.headers.get("x-desk-token", "").strip()
    if header:
        return header
    if session_valid(request.cookies.get(COOKIE_NAME)):
        return (settings.desk_token or "").strip()
    return ""


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
async def desk_status(request: Request):
    return {"configured": desk_configured(), "authenticated": request_authenticated(request)}


@router.post("/api/desk/login")
async def desk_login(body: DeskLoginBody, request: Request):
    expected = (settings.desk_token or "").strip()
    if not expected:
        raise HTTPException(status_code=403, detail="Biurko zamknięte. Ustaw CYCLICAL_DESK_TOKEN.")
    if tokens_match(body.token or "", expected):
        note_login_success(request)
        response = JSONResponse({"ok": True})
        _set_session_cookie(response, request, issue_session())
        return response
    failures = note_login_failure(request)
    if failures > _LOGIN_MAX:
        raise HTTPException(
            status_code=429,
            detail="Za dużo błędnych prób z tego adresu. Poprawny token nadal wchodzi.",
            headers={"Retry-After": "60"},
        )
    raise HTTPException(status_code=401, detail="Zły token biurka.")


@router.post("/api/desk/logout")
async def desk_logout(request: Request):
    drop_session(request.cookies.get(COOKIE_NAME))
    response = JSONResponse({"ok": True})
    _clear_session_cookie(response, request)
    return response


class DeskAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS or request.url.path in {_LOGIN_PATH, _LOGOUT_PATH}:
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
        if not csrf_ok(request):
            return JSONResponse(status_code=403, content={"detail": "Żądanie spoza biurka."})
        header = request.headers.get("x-desk-token", "")
        if header:
            if tokens_match(header, expected):
                note_login_success(request)
                return await call_next(request)
            if note_login_failure(request) > _LOGIN_MAX:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Za dużo błędnych prób z tego adresu. Poprawny token nadal wchodzi."},
                )
            return JSONResponse(status_code=401, content={"detail": "Zły token biurka."})
        if session_valid(request.cookies.get(COOKIE_NAME)):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={"detail": "Zaloguj biurko, żeby zmienić stan."},
        )
