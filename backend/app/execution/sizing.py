"""Position sizing for execution agent."""

from __future__ import annotations

from app.config import settings


def compute_amount_pln(override: float | None = None) -> float:
    return float(override if override is not None else settings.execution_amount_pln)
