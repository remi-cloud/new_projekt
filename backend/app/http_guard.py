"""Security headers, same-site CORS list, and a small POST rate limit."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

_HITS: dict[str, deque[float]] = defaultdict(deque)

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' ws: wss:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def is_dev() -> bool:
    return settings.app_env.strip().lower() in {"dev", "development", "local"}


def cors_origin_list() -> list[str]:
    origins: list[str] = []
    for raw in (settings.cors_origins or "").split(","):
        item = raw.strip().rstrip("/")
        if item and item not in origins:
            origins.append(item)
    public = (settings.public_base_url or "").strip().rstrip("/")
    if public and public not in origins:
        origins.append(public)
    if is_dev():
        for local in (
            "http://127.0.0.1:8080",
            "http://localhost:8080",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ):
            if local not in origins:
                origins.append(local)
    return origins


def _client_key(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = _CSP
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        if proto == "https" and not is_dev():
            response.headers["Strict-Transport-Security"] = "max-age=15552000; includeSubDomains"
        return response


class PostRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "POST":
            return await call_next(request)
        limit = max(1, int(settings.post_rate_limit or 120))
        window = max(1, int(settings.post_rate_window_seconds or 60))
        now = time.monotonic()
        bucket = _HITS[_client_key(request)]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Zbyt wiele żądań POST. Spróbuj za chwilę."},
            )
        bucket.append(now)
        return await call_next(request)
