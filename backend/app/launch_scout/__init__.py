"""Launch Scout — multi-DEX low-MC entry agent."""

from __future__ import annotations

from typing import Any, Callable

__all__ = [
    "get_launch_status",
    "list_launch_candidates",
    "run_launch_scout_tick",
]


def __getattr__(name: str) -> Callable[..., Any]:
    if name in __all__:
        from app.launch_scout import service as _service

        return getattr(_service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
