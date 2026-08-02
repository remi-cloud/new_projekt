"""Global LONG and SHORT scout agents — equal roster, world coverage."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.types import (
    REGION_LABELS,
    RegionClass,
    ScoutFinding,
    ScoutUniverse,
    SideBias,
)
from app.agents.universes import default_universes
from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    BetaModelStatus,
    SignalAction,
)

logger = logging.getLogger(__name__)

REGIONS: tuple[RegionClass, ...] = (
    "us_equity",
    "global_equity",
    "crypto",
    "bonds",
    "commodities",
    "forex",
)


class ScoutAgent:
    """One scout hunts only one side (long XOR short) in one global region."""

    def __init__(self, side: SideBias, region: RegionClass, universe: ScoutUniverse) -> None:
        self.side = side
        self.region = region
        self.universe = universe
        self.scout_id = f"{side}.{region}"
        self.label = f"{side.upper()} · {REGION_LABELS.get(region, region)}"

    def covers(self, quote: AssetQuote) -> bool:
        allowed = {s.upper() for s in self.universe.symbols}
        if allowed:
            return quote.symbol.upper() in allowed
        return quote.asset_class in self.universe.asset_classes

    async def scout(
        self,
        quotes: list[AssetQuote],
        *,
        alpha: AlphaModelStatus | None,
        beta: BetaModelStatus | None,
    ) -> list[ScoutFinding]:
        findings: list[ScoutFinding] = []
        for quote in quotes:
            if not self.covers(quote):
                continue
            finding = self._score(quote, alpha=alpha, beta=beta)
            if finding:
                findings.append(finding)
        findings.sort(key=lambda f: f.confidence, reverse=True)
        logger.info(
            "Scout %s: %d quotes covered → %d %s findings",
            self.scout_id,
            sum(1 for q in quotes if self.covers(q)),
            len(findings),
            self.side,
        )
        return findings

    def _score(
        self,
        quote: AssetQuote,
        *,
        alpha: AlphaModelStatus | None,
        beta: BetaModelStatus | None,
    ) -> ScoutFinding | None:
        chg7 = quote.change_pct_7d
        chg24 = quote.change_pct_24h
        factors: list[dict] = []

        if quote.asset_class == AssetClass.CRYPTO and alpha:
            return self._score_crypto(quote, alpha, chg7, chg24, factors)
        if beta:
            return self._score_traditional(quote, beta, chg7, chg24, factors)
        return None

    def _score_crypto(
        self,
        quote: AssetQuote,
        alpha: AlphaModelStatus,
        chg7: float | None,
        chg24: float | None,
        factors: list[dict],
    ) -> ScoutFinding | None:
        phase = alpha.phase.value
        signal = alpha.signal
        conf = 50.0
        wants_long = False
        wants_short = False

        if phase == "bear":
            if signal == SignalAction.SELL:
                wants_short = True
                conf = 60 + (100 - alpha.phase_progress_pct) * 0.2
                factors.append({"name": "Alpha early bear", "detail": "SHORT bias"})
            elif signal == SignalAction.BUY:
                wants_long = True
                conf = 52 + alpha.phase_progress_pct * 0.25
                factors.append({"name": "Alpha late bear", "detail": "LONG accumulation"})
            elif signal == SignalAction.WATCH:
                if chg7 is not None and chg7 < -8:
                    wants_short = True
                    conf = 58 + min(abs(chg7), 12)
                else:
                    wants_long = True
                    conf = 50
        elif phase == "bull":
            if signal == SignalAction.BUY:
                wants_long = True
                conf = 65
                if chg7 is not None and chg7 > 12:
                    wants_long = False
                    wants_short = True
                    conf = 62
                    factors.append({"name": "Melt-up", "detail": f"7d {chg7:+.1f}%"})
            elif signal == SignalAction.HOLD:
                if chg7 is not None and chg7 > 10:
                    wants_short = True
                    conf = 58
                else:
                    return None
        elif phase == "distribution":
            wants_short = True
            conf = 72
            factors.append({"name": "Alpha distribution", "detail": "SHORT"})

        if self.side == "long" and not wants_long:
            return None
        if self.side == "short" and not wants_short:
            return None

        if self.side == "short" and chg7 is not None and chg7 < -4:
            conf += 8
        if self.side == "long" and chg7 is not None and chg7 < -3:
            conf += 6

        if conf < 48:
            return None

        return self._finding(
            quote,
            confidence=min(conf, 95),
            phase=phase,
            cycle_source="alpha",
            rationale=f"Scout {self.scout_id}: {alpha.rationale}",
            factors=factors,
            chg7=chg7,
            chg24=chg24,
        )

    def _score_traditional(
        self,
        quote: AssetQuote,
        beta: BetaModelStatus,
        chg7: float | None,
        chg24: float | None,
        factors: list[dict],
    ) -> ScoutFinding | None:
        phase_n = beta.phase_number
        prior = beta.signal
        weak = phase_n in (1, 2) or prior == SignalAction.SELL
        strong = phase_n == 3 or prior == SignalAction.BUY
        conf = 50.0
        wants_long = False
        wants_short = False

        # Bonds often hedge: LONG bonds when equity SHORT regime
        if quote.asset_class == AssetClass.BOND:
            if weak:
                wants_long = True
                conf = 58
                factors.append({"name": "Bond hedge", "detail": "risk-off → LONG bonds"})
            elif strong and chg7 is not None and chg7 > 2:
                wants_short = True
                conf = 54
            else:
                return None
        elif weak:
            # Weak regime: SHORT rallies, LONG deep dumps
            if chg7 is not None and chg7 >= 1.5:
                wants_short = True
                conf = 56 + min(chg7, 12) * 1.6
                factors.append({"name": "Fade rally", "detail": f"7d {chg7:+.1f}% in weak phase"})
            elif chg7 is not None and chg7 <= -5:
                wants_long = True
                conf = 54 + min(abs(chg7), 12) * 1.2
                factors.append({"name": "Bounce dump", "detail": f"7d {chg7:+.1f}%"})
            elif chg24 is not None and chg24 >= 1.2:
                wants_short = True
                conf = 55 + chg24 * 2
            else:
                # Phase prior alone
                if prior in (SignalAction.SELL, SignalAction.WATCH):
                    wants_short = True
                    conf = 52 + (10 if phase_n in (1, 2) else 0)
                    factors.append({"name": "Phase prior", "detail": f"Beta {prior.value} → SHORT"})
                elif prior == SignalAction.BUY:
                    wants_long = True
                    conf = 52
        elif strong:
            if chg7 is not None and chg7 <= -2.5:
                wants_long = True
                conf = 56 + min(abs(chg7), 12) * 1.4
                factors.append({"name": "Dip buy", "detail": f"7d {chg7:+.1f}%"})
            elif chg7 is not None and chg7 >= 8:
                wants_short = True
                conf = 57 + min(chg7 - 8, 10) * 1.4
                factors.append({"name": "Overbought", "detail": f"7d {chg7:+.1f}%"})
            else:
                wants_long = True
                conf = 55 + (12 if quote.asset_class in (AssetClass.STOCK, AssetClass.INDEX) else 0)
                factors.append({"name": "Phase 3/BUY prior", "detail": "LONG bias"})
        else:
            # Phase 4 mixed
            if chg7 is not None and chg7 >= 3:
                wants_short = True
                conf = 54 + min(chg7, 10) * 1.3
            elif chg7 is not None and chg7 <= -3:
                wants_long = True
                conf = 54 + min(abs(chg7), 10) * 1.3
            elif prior == SignalAction.SELL:
                wants_short = True
                conf = 53
            else:
                return None

        if self.side == "long" and not wants_long:
            return None
        if self.side == "short" and not wants_short:
            return None
        if conf < 48:
            return None

        # Index/stock conviction bump for matching side
        if quote.asset_class in (AssetClass.STOCK, AssetClass.INDEX):
            if self.side == "short" and phase_n in (1, 2):
                conf += 10
            if self.side == "long" and phase_n == 3:
                conf += 10

        return self._finding(
            quote,
            confidence=min(conf, 95),
            phase=beta.current_phase.value,
            cycle_source="beta",
            rationale=(
                f"Scout {self.scout_id}: Model Beta faza {phase_n} → "
                f"{'LONG' if self.side == 'long' else 'SHORT'}. {beta.historical_bias}"
                + (f" 7d {chg7:+.1f}%." if chg7 is not None else "")
            ),
            factors=factors,
            chg7=chg7,
            chg24=chg24,
        )

    def _finding(
        self,
        quote: AssetQuote,
        *,
        confidence: float,
        phase: str,
        cycle_source: str,
        rationale: str,
        factors: list[dict],
        chg7: float | None,
        chg24: float | None,
    ) -> ScoutFinding:
        return ScoutFinding(
            scout_id=self.scout_id,
            side=self.side,
            region=self.region,
            symbol=quote.symbol,
            name=quote.name,
            asset_class=quote.asset_class,
            price=quote.price,
            confidence=round(confidence, 1),
            phase=phase,
            cycle_source=cycle_source,
            rationale=rationale,
            change_pct_7d=chg7,
            change_pct_24h=chg24,
            factors=factors,
        )


def build_scout_roster(watchlist: list[dict] | None = None) -> list[ScoutAgent]:
    """Exactly 12 scouts: 6 LONG + 6 SHORT, one pair per global region."""
    universes = default_universes(watchlist)
    roster: list[ScoutAgent] = []
    for region in REGIONS:
        uni = universes[region]
        roster.append(ScoutAgent("long", region, uni))
        roster.append(ScoutAgent("short", region, uni))
    assert len(roster) == 12
    assert sum(1 for s in roster if s.side == "long") == sum(
        1 for s in roster if s.side == "short"
    )
    return roster
