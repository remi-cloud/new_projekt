"""System coordinator — health ticks + link guard."""

from app.coordinator.service import get_coordinator_health, run_coordinator_tick

__all__ = ["get_coordinator_health", "run_coordinator_tick"]
