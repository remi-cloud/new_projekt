"""Shared types for regional macro cycle analysis."""

from dataclasses import dataclass

from app.models.schemas import SignalAction


@dataclass(frozen=True)
class MacroCycleResult:
    cycle_id: str
    phase: str
    signal: SignalAction
    buy_weight: float
    bias: str
    rationale: str

    @property
    def base_confidence(self) -> float:
        """Map buy_weight to a 0–100 confidence baseline for signal combiner."""
        return 35 + self.buy_weight * 50
