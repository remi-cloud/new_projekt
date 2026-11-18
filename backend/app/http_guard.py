"""Security headers, same-site CORS list, and a small POST rate limit."""

from __future__ import annotations

import ipaddress
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.public_surface import PUBLIC_WRITE_PATHS

_HITS: dict[str, deque[float]] = defaultdict(deque)

# The sha256 allows the one stylesheet lightweight-charts injects for the attribution mark.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://s3.tradingview.com; "
    "frame-src https://www.tradingview.com https://s.tradingview.com https://www.tradingview-widget.com; "
    "style-src 'self' https://fonts.googleapis.com 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='; "
    "style-src-attr 'unsafe-inline'; "
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


def _peer_host(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _trusted_proxy(host: str) -> bool:
    raw = (settings.trusted_proxies or "").strip()
    if not raw or not host:
        return False
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        if token == host:
            return True
        try:
            if ipaddress.ip_address(host) in ipaddress.ip_network(token, strict=False):
                return True
        except ValueError:
            continue
    return False


def request_is_https(request: Request) -> bool:
    """True when the browser connection is HTTPS.

    Nginx talks HTTP to the app. X-Forwarded-Proto is honored only from a
    trusted proxy, so a visitor cannot turn on the Secure cookie or HSTS.
    """
    scheme = (request.url.scheme or "").lower()
    peer = request.client.host if request.client else ""
    if _trusted_proxy(peer):
        forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        if forwarded in {"https", "http"}:
            scheme = forwarded
    return scheme == "https"


def client_key(request: Request) -> str:
    """Socket peer, unless that peer is a trusted proxy.

    A client-supplied X-Forwarded-For is ignored. Behind a trusted proxy the
    rightmost untrusted hop is the address that proxy actually saw.
    """
    peer = _peer_host(request)
    if not _trusted_proxy(peer):
        return peer
    hops = [hop.strip() for hop in (request.headers.get("x-forwarded-for") or "").split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _trusted_proxy(hop):
            return hop
    return peer


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = _CSP
        if request_is_https(request) and not is_dev():
            response.headers["Strict-Transport-Security"] = "max-age=15552000; includeSubDomains"
        return response


class PostRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)
        path = request.url.path
        key = client_key(request)
        if path == "/api/desk/login":
            # High ceiling only. Wrong passwords are backed off in desk_auth,
            # and a correct token is never rejected by that counter.
            limit, window, bucket_key = 40, 60, f"login:{key}"
        elif path in PUBLIC_WRITE_PATHS:
            limit, window, bucket_key = 20, 60, f"guest:{key}"
        else:
            limit = max(1, int(settings.post_rate_limit or 120))
            window = max(1, int(settings.post_rate_window_seconds or 60))
            bucket_key = key
        now = time.monotonic()
        bucket = _HITS[bucket_key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Zbyt wiele żądań POST. Spróbuj za chwilę."},
            )
        bucket.append(now)
        return await call_next(request)
