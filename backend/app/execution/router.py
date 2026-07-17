"""Route signals to the appropriate broker adapter."""

from __future__ import annotations

from app.config import settings
from app.data.broker_map import resolve_execution_brokers
from app.execution.brokers import get_broker_adapter
from app.execution.models import SignalCandidate


def route_broker(candidate: SignalCandidate) -> tuple[str, str | None]:
    """Return (primary_broker_id, fallback_broker_id)."""
    primary, fallback = resolve_execution_brokers(
        candidate.symbol,
        candidate.asset_class,
        candidate.region,
        broker_crypto=settings.execution_broker_crypto,
        broker_equity=settings.execution_broker_equity,
        broker_equity_fallback=settings.execution_broker_equity_fallback,
    )
    return primary, fallback


def pick_configured_broker(candidate: SignalCandidate) -> str | None:
    primary, fallback = route_broker(candidate)
    for bid in (primary, fallback):
        if not bid:
            continue
        try:
            adapter = get_broker_adapter(bid)
        except KeyError:
            continue
        # Synchronous check not available — caller uses async is_configured
        return bid
    return primary
