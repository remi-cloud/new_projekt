"""LONG and SHORT AI specialists — referee scout findings into final opportunities."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

from app.agents.types import ScoutFinding, SpecialistVerdict
from app.models.schemas import (
    AlphaModelStatus,
    AssetQuote,
    BetaModelStatus,
    Opportunity,
    SignalAction,
)

logger = logging.getLogger(__name__)


class SideSpecialist:
    """AI specialist for one side. Draws conclusions from all scout findings on that side."""

    def __init__(self, side: str) -> None:
        assert side in ("long", "short")
        self.side = side
        self.label = (
            "Singularity LONG" if side == "long" else "Singularity SHORT"
        )

    def evaluate(
        self,
        findings: list[ScoutFinding],
        *,
        alpha: AlphaModelStatus | None,
        beta: BetaModelStatus | None,
        now: datetime | None = None,
        top_n: int = 16,
    ) -> list[SpecialistVerdict]:
        now = now or datetime.now(timezone.utc)
        # Cluster by symbol — multiple scouts may agree
        by_sym: dict[str, list[ScoutFinding]] = {}
        for f in findings:
            by_sym.setdefault(f.symbol, []).append(f)

        verdicts: list[SpecialistVerdict] = []
        for symbol, group in by_sym.items():
            group.sort(key=lambda x: x.confidence, reverse=True)
            best = group[0]
            scout_ids = [g.scout_id for g in group]
            # Agreement bonus
            agreement = len(group)
            conf = best.confidence + min(8.0, (agreement - 1) * 4.0)

            # Specialist cross-check vs cycle models
            model_boost, model_note = self._model_alignment(best, alpha, beta)
            conf = max(0.0, min(98.0, conf + model_boost))

            # Trend veto: don't bless SHORT when tape is clearly LONG
            trend_penalty, trend_note = self._trend_gate(best)
            conf = max(0.0, min(98.0, conf + trend_penalty))

            factors = [
                {
                    "name": "Scout consensus",
                    "detail": f"{agreement} scout(ów): {', '.join(scout_ids)}",
                    "weight": round(best.confidence, 1),
                },
                {
                    "name": "Model alignment",
                    "detail": model_note,
                    "weight": round(model_boost, 1),
                },
                {
                    "name": "Trend gate",
                    "detail": trend_note,
                    "weight": round(trend_penalty, 1),
                },
                *best.factors,
            ]

            accepted = conf >= 55.0 and trend_penalty > -20
            action = SignalAction.BUY if self.side == "long" else SignalAction.SELL
            opp = None
            if accepted:
                opp = Opportunity(
                    symbol=best.symbol,
                    name=best.name,
                    asset_class=best.asset_class,
                    action=action,
                    confidence=round(conf, 1),
                    cycle_source=best.cycle_source,
                    phase=best.phase,
                    price=best.price,
                    rationale=(
                        f"{self.label}: {best.rationale} "
                        f"| consensus×{agreement} | {model_note}"
                    ),
                    created_at=now,
                )

            label = "LONG" if self.side == "long" else "SHORT"
            verdicts.append(
                SpecialistVerdict(
                    side=self.side,  # type: ignore[arg-type]
                    symbol=symbol,
                    name=best.name,
                    asset_class=best.asset_class,
                    accepted=accepted,
                    confidence=round(conf, 1),
                    summary=(
                        f"{self.label} → {'AKCEPTUJ' if accepted else 'ODRZUĆ'} {label} "
                        f"{symbol} ({conf:.0f}%)"
                    ),
                    scout_ids=scout_ids,
                    factors=factors,
                    opportunity=opp,
                )
            )

        verdicts.sort(key=lambda v: v.confidence, reverse=True)
        accepted_n = sum(1 for v in verdicts if v.accepted)
        logger.info(
            "%s: %d symbols from scouts → %d accepted (top_n=%d)",
            self.label,
            len(verdicts),
            accepted_n,
            top_n,
        )
        return [v for v in verdicts if v.accepted][:top_n]

    def _trend_gate(self, finding: ScoutFinding) -> tuple[float, str]:
        """Block nonsense: SHORT while market is climbing / LONG while dumping hard."""
        chg7 = finding.change_pct_7d
        chg24 = finding.change_pct_24h
        if self.side == "short":
            if chg7 is not None and chg7 >= 1.5 and (chg24 is None or chg24 >= -1.0):
                if chg7 < 10:
                    return -25.0, f"Veto SHORT: rynek idzie LONG (7d {chg7:+.1f}%)"
                return -4.0, f"Ostrożny SHORT przy silnym rajdzie 7d {chg7:+.1f}%"
            return 0.0, "Trend OK dla SHORT"
        # long side
        if chg7 is not None and chg7 <= -3.0 and (chg24 is None or chg24 <= 0):
            if chg7 > -8:
                return -8.0, f"Ostrożny LONG przy spadku 7d {chg7:+.1f}%"
        if chg7 is not None and chg7 >= 1.0:
            return 6.0, f"Trend LONG potwierdza (7d {chg7:+.1f}%)"
        return 0.0, "Trend OK dla LONG"

    def _model_alignment(
        self,
        finding: ScoutFinding,
        alpha: AlphaModelStatus | None,
        beta: BetaModelStatus | None,
    ) -> tuple[float, str]:
        if finding.cycle_source == "alpha" and alpha:
            if self.side == "short" and alpha.signal == SignalAction.SELL:
                return 8.0, "Alpha potwierdza SHORT"
            if self.side == "long" and alpha.signal in (SignalAction.BUY, SignalAction.WATCH):
                return 6.0, "Alpha wspiera LONG"
            if self.side == "short" and alpha.signal == SignalAction.BUY:
                return -6.0, "Alpha woli LONG — kara"
            if self.side == "long" and alpha.signal == SignalAction.SELL:
                return -6.0, "Alpha woli SHORT — kara"
        if finding.cycle_source == "beta" and beta:
            if self.side == "short" and beta.signal == SignalAction.SELL:
                return 8.0, "Beta potwierdza SHORT"
            if self.side == "long" and beta.signal == SignalAction.BUY:
                return 8.0, "Beta potwierdza LONG"
            if self.side == "short" and beta.phase_number in (1, 2):
                return 5.0, "Beta faza słaba — SHORT OK"
            if self.side == "long" and beta.phase_number == 3:
                return 5.0, "Beta faza silna — LONG OK"
            if self.side == "short" and beta.signal == SignalAction.BUY and beta.phase_number == 3:
                return -4.0, "Beta silny BUY — ostrożny SHORT"
        return 0.0, "Brak mocnego alignmentu modelu"

    @staticmethod
    def to_opportunities(verdicts: Iterable[SpecialistVerdict]) -> list[Opportunity]:
        return [v.opportunity for v in verdicts if v.accepted and v.opportunity]


class LongSpecialist(SideSpecialist):
    def __init__(self) -> None:
        super().__init__("long")


class ShortSpecialist(SideSpecialist):
    def __init__(self) -> None:
        super().__init__("short")
