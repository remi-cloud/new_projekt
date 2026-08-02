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
                # Mid/late bear WATCH: only soft LONG (DCA) if tape not dumping hard
                if chg7 is not None and chg7 < -6:
                    wants_short = True
                    conf = 56 + min(abs(chg7), 10)
                    factors.append(
                        {
                            "name": "Alpha bear + dump",
                            "detail": f"Faza spadkowa + 7d {chg7:+.1f}% → nie łap noży (SHORT/czekaj)",
                        }
                    )
                elif alpha.phase_progress_pct >= 55:
                    # Late bear DCA — soft long only, never scream
                    wants_long = True
                    conf = 48 + min(alpha.phase_progress_pct * 0.12, 10)
                    factors.append(
                        {
                            "name": "Alpha late bear DCA",
                            "detail": "Wcześniejszy SHORT minął; teraz tylko ostrożna akumulacja (nie all-in)",
                        }
                    )
                else:
                    return None
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
        """
        Trend-first scoring. Phase prior is a soft bias only — never invert
        a clear uptrend into SHORT just because Beta says historically weak.
        """
        phase_n = beta.phase_number
        prior = beta.signal
        conf = 50.0
        wants_long = False
        wants_short = False

        # Bonds: hedge when equities dump; otherwise follow bond momentum
        if quote.asset_class == AssetClass.BOND:
            if chg7 is not None and chg7 <= -2:
                wants_long = True
                conf = 58 + min(abs(chg7), 8)
                factors.append({"name": "Bond dip", "detail": f"7d {chg7:+.1f}% → LONG"})
            elif chg7 is not None and chg7 >= 2.5 and phase_n == 3:
                wants_short = True
                conf = 54
                factors.append({"name": "Bond stretch", "detail": f"7d {chg7:+.1f}%"})
            elif chg7 is not None and chg7 >= 0.5:
                wants_long = True
                conf = 54
                factors.append({"name": "Bond bid", "detail": "momentum LONG"})
            else:
                return None
        else:
            uptrend = self._is_uptrend(chg7, chg24)
            downtrend = self._is_downtrend(chg7, chg24)
            melt_up = chg7 is not None and chg7 >= 10 and (chg24 is None or chg24 > 1.5)

            if uptrend and not melt_up:
                # Clear LONG tape — do NOT fade because of weak-phase calendar
                wants_long = True
                conf = 58 + min(max(chg7 or 0, 0), 10) * 1.5
                if chg24 is not None and chg24 > 0:
                    conf += min(chg24, 4) * 1.2
                factors.append(
                    {
                        "name": "Trend LONG",
                        "detail": (
                            f"Rynek idzie w górę (7d {chg7:+.1f}%"
                            + (f", 24h {chg24:+.1f}%" if chg24 is not None else "")
                            + ") — Singularity trzyma LONG"
                        ),
                    }
                )
                # Soft phase note (not a side flip)
                if phase_n in (1, 2):
                    conf -= 3
                    factors.append(
                        {
                            "name": "Phase caution",
                            "detail": f"Beta faza {phase_n} historycznie słabsza — lekka kara, bez flipu na SHORT",
                        }
                    )
                elif phase_n == 3 or prior == SignalAction.BUY:
                    conf += 8
                    factors.append({"name": "Phase align", "detail": "Beta wspiera LONG"})

            elif downtrend:
                wants_short = True
                conf = 58 + min(abs(chg7 or 0), 10) * 1.5
                factors.append(
                    {
                        "name": "Trend SHORT",
                        "detail": f"Rynek spada (7d {chg7:+.1f}%) — Singularity SHORT",
                    }
                )
                if phase_n in (1, 2) or prior == SignalAction.SELL:
                    conf += 6
                    factors.append({"name": "Phase align", "detail": "Beta wspiera SHORT"})

            elif melt_up:
                # Only tactical SHORT when truly stretched + still accelerating
                wants_short = True
                conf = 56 + min((chg7 or 0) - 10, 8) * 1.2
                factors.append(
                    {
                        "name": "Melt-up fade",
                        "detail": f"Ekstremalne przegrzanie 7d {chg7:+.1f}% — taktyczny SHORT",
                    }
                )

            else:
                # Flat / mixed tape — soft phase prior only
                if prior == SignalAction.BUY or (phase_n == 3 and prior != SignalAction.SELL):
                    wants_long = True
                    conf = 52
                    factors.append({"name": "Phase prior", "detail": "Płaski rynek → LONG z Beta"})
                elif prior == SignalAction.SELL and phase_n in (1, 2, 4):
                    wants_short = True
                    conf = 51
                    factors.append({"name": "Phase prior", "detail": "Płaski rynek → ostrożny SHORT z Beta"})
                else:
                    # WATCH / mixed: prefer LONG if any green, else skip
                    if chg7 is not None and chg7 > 0:
                        wants_long = True
                        conf = 52
                        factors.append({"name": "Slight green", "detail": "Lekki plus → LONG"})
                    elif chg7 is not None and chg7 < -1:
                        wants_short = True
                        conf = 52
                        factors.append({"name": "Slight red", "detail": "Lekki minus → SHORT"})
                    else:
                        return None

        if self.side == "long" and not wants_long:
            return None
        if self.side == "short" and not wants_short:
            return None
        if conf < 48:
            return None

        if quote.asset_class in (AssetClass.STOCK, AssetClass.INDEX) and self.side == "long":
            if self._is_uptrend(chg7, chg24):
                conf += 6
            if phase_n == 3:
                conf += 6

        return self._finding(
            quote,
            confidence=min(conf, 95),
            phase=beta.current_phase.value,
            cycle_source="beta",
            rationale=(
                f"Scout {self.scout_id}: "
                f"{'LONG' if self.side == 'long' else 'SHORT'} "
                f"(trend-first, Beta faza {phase_n})."
                + (f" 7d {chg7:+.1f}%." if chg7 is not None else "")
            ),
            factors=factors,
            chg7=chg7,
            chg24=chg24,
        )

    @staticmethod
    def _is_uptrend(chg7: float | None, chg24: float | None) -> bool:
        if chg7 is not None and chg7 >= 1.5:
            # Don't call it uptrend if last day is a hard dump
            if chg24 is not None and chg24 <= -2.5:
                return False
            return True
        if chg7 is not None and chg7 >= 0.6 and chg24 is not None and chg24 >= 0.8:
            return True
        return False

    @staticmethod
    def _is_downtrend(chg7: float | None, chg24: float | None) -> bool:
        if chg7 is not None and chg7 <= -2.0:
            if chg24 is not None and chg24 >= 2.5:
                return False  # bounce day
            return True
        if chg7 is not None and chg7 <= -0.8 and chg24 is not None and chg24 <= -1.0:
            return True
        return False

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
