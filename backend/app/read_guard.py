"""Cooldown for guest-triggered heavy reads. Panels still use a warm cache."""

from __future__ import annotations

import time

WINDOW_SECONDS = 60.0
_last: dict[str, float] = {}


def reset_read_guard() -> None:
    _last.clear()


def forced_refresh_due(key: str, *, window: float = WINDOW_SECONDS) -> bool:
    """True when a forced refresh may run. A hit within the window returns False."""
    now = time.monotonic()
    last = _last.get(key, 0.0)
    if last and now - last < window:
        return False
    _last[key] = now
    return True
