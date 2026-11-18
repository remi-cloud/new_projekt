"""Keep browser-facing links off the loopback dev origin."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from app.config import settings

# Dev WWW only. Ollama (:11434) and other local ports stay as server-side config.
_LOOPBACK_8080 = re.compile(
    r"^https?://(?:127\.0\.0\.1|localhost):8080(?=/|$)",
    re.IGNORECASE,
)


def strip_loopback_origin(url: str | None) -> str | None:
    """Turn http://127.0.0.1:8080/path into /path. Other URLs pass through."""
    if url is None:
        return None
    text = url.strip()
    if not text:
        return text
    match = _LOOPBACK_8080.match(text)
    if not match:
        return text
    rest = text[match.end() :]
    if not rest:
        return ""
    return rest if rest.startswith("/") else f"/{rest}"


def public_site_base() -> str:
    """Absolute public origin for footers. Loopback is treated as unset."""
    raw = (settings.public_base_url or "").strip().rstrip("/")
    if not raw:
        return ""
    stripped = strip_loopback_origin(raw) or ""
    if not stripped or stripped.startswith("/"):
        return ""
    return stripped.rstrip("/")


def live_domain_ready() -> bool:
    """True only when the public site URL is https on a real hostname.

    Loopback, raw IPs and quick tunnels are not Robi's domain, so auto-X waits.
    """
    base = public_site_base()
    if not base.lower().startswith("https://"):
        return False
    host = (urlparse(base).hostname or "").lower().rstrip(".")
    if not host or "." not in host:
        return False
    if host in {"localhost"} or host.endswith(".local") or host.endswith(".trycloudflare.com"):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return True
    return False
