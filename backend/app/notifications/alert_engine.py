"""Detect signal/price changes worth notifying."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.schemas import AssetCycleAssessment, SignalAction


@dataclass(frozen=True)
class AlertEvent:
    symbol: str
    name: str
    action: str
    confidence: float
    price: float
    reason: str
    previous_action: str | None = None


class AlertEngine:
    def __init__(self) -> None:
        self._last_signals: dict[str, tuple[str, float, float]] = {}
        self._last_sent: dict[str, datetime] = {}

    def reset(self, assessments: list[AssetCycleAssessment]) -> None:
        self._last_signals = {
            a.symbol: (a.signal.value, a.confidence, a.price) for a in assessments
        }

    def diff(
        self,
        assessments: list[AssetCycleAssessment],
        *,
        min_confidence: float | None = None,
    ) -> list[AlertEvent]:
        min_conf = min_confidence if min_confidence is not None else settings.alert_min_confidence
        cooldown = timedelta(minutes=settings.alert_cooldown_minutes)
        now = datetime.now(timezone.utc)
        events: list[AlertEvent] = []

        for a in assessments:
            prev = self._last_signals.get(a.symbol)
            last_sent = self._last_sent.get(a.symbol)

            if last_sent and now - last_sent < cooldown:
                continue

            if a.confidence < min_conf:
                continue

            if a.signal not in (SignalAction.BUY, SignalAction.SELL):
                continue

            if not prev:
                events.append(
                    AlertEvent(
                        symbol=a.symbol,
                        name=a.name,
                        action=a.signal.value,
                        confidence=a.confidence,
                        price=a.price,
                        reason="Nowy sygnał wysokiej pewności",
                    )
                )
                continue

            prev_action, prev_conf, prev_price = prev
            if prev_action != a.signal.value:
                events.append(
                    AlertEvent(
                        symbol=a.symbol,
                        name=a.name,
                        action=a.signal.value,
                        confidence=a.confidence,
                        price=a.price,
                        reason=f"Zmiana sygnału: {prev_action} → {a.signal.value}",
                        previous_action=prev_action,
                    )
                )
                continue

            if prev_price > 0:
                move_pct = abs((a.price - prev_price) / prev_price * 100)
                if move_pct >= 2.0 and a.confidence >= min_conf + 5:
                    events.append(
                        AlertEvent(
                            symbol=a.symbol,
                            name=a.name,
                            action=a.signal.value,
                            confidence=a.confidence,
                            price=a.price,
                            reason=f"Ruch ceny {move_pct:.1f}% przy sygnale {a.signal.value}",
                            previous_action=prev_action,
                        )
                    )

        for e in events:
            self._last_sent[e.symbol] = now

        self._last_signals = {
            a.symbol: (a.signal.value, a.confidence, a.price) for a in assessments
        }
        return events


alert_engine = AlertEngine()
