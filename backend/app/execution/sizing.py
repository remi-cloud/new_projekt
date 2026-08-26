"""Position sizing for execution agent."""

from __future__ import annotations

from app.config import settings


def confidence_size_mult(confidence: float | None) -> float:
    if confidence is None:
        return 1.0
    if confidence < 75:
        return 0.5
    if confidence >= 85:
        return 1.25
    return 1.0


def reward_risk_size_mult(reward_risk: float | None) -> float | None:
    """Return size multiplier, or None if proposal should be blocked (R:R < 1)."""
    if reward_risk is None:
        return 1.0
    if reward_risk < 1.0:
        return None
    if reward_risk < 1.4:
        return 0.5
    return 1.0


def compute_amount_pln(
    override: float | None = None,
    *,
    confidence: float | None = None,
    reward_risk: float | None = None,
) -> float:
    """Base amount scaled by confidence band and optional R:R gate.

    Returns 0 when R:R is present and &lt; 1 (caller should skip the proposal).
    """
    base = float(override if override is not None else settings.execution_amount_pln)
    rr_mult = reward_risk_size_mult(reward_risk)
    if rr_mult is None:
        return 0.0
    mult = confidence_size_mult(confidence) * rr_mult
    return round(max(0.0, base * mult), 2)
