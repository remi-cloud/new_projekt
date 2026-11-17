"""Keep browser-facing links off the loopback dev origin."""

from __future__ import annotations

import re

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
