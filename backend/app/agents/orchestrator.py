"""
Final developer / orchestrator.

Pipeline:
  6 LONG scouts + 6 SHORT scouts (global)
    → AI Specjalista LONG + AI Specjalista SHORT
      → Orchestrator merges balanced book for the product
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.scouts import ScoutAgent, build_scout_roster
from app.agents.specialists import LongSpecialist, ShortSpecialist
from app.agents.types import AgentScanResult, ScoutFinding, SpecialistVerdict
from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes
from app.db.settings_store import get_watchlist
from app.models.schemas import (
    AlphaModelStatus,
    AssetQuote,
    BetaModelStatus,
    Opportunity,
    SignalAction,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Torpedo control room — all scouts + specialists report here."""

    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.opportunities: list[Opportunity] = []
        self.quotes: list[AssetQuote] = []
        self.alpha_model: AlphaModelStatus | None = None
        self.beta_model: BetaModelStatus | None = None
        self.last_result: AgentScanResult | None = None
        self._scouts: list[ScoutAgent] = []
        self.long_specialist = LongSpecialist()
        self.short_specialist = ShortSpecialist()

    @property
    def bitcoin_cycle(self) -> AlphaModelStatus | None:
        return self.alpha_model

    @property
    def presidential_cycle(self) -> BetaModelStatus | None:
        return self.beta_model

    def roster_status(self) -> dict[str, Any]:
        result = self.last_result
        long_scouts = [s for s in self._scouts if s.side == "long"]
        short_scouts = [s for s in self._scouts if s.side == "short"]
        return {
            "module": "Singularity",
            "pipeline": "scouts → specialists → Singularity orchestrator",
            "long_scouts": [
                {
                    "id": s.scout_id,
                    "label": s.label,
                    "symbols": len(s.universe.symbols),
                    "region": s.region,
                }
                for s in long_scouts
            ],
            "short_scouts": [
                {
                    "id": s.scout_id,
                    "label": s.label,
                    "symbols": len(s.universe.symbols),
                    "region": s.region,
                }
                for s in short_scouts
            ],
            "counts": {
                "long_scouts": len(long_scouts),
                "short_scouts": len(short_scouts),
                "equal": len(long_scouts) == len(short_scouts),
            },
            "specialists": [
                {"id": "specialist.long", "label": self.long_specialist.label},
                {"id": "specialist.short", "label": self.short_specialist.label},
            ],
            "orchestrator": {"id": "singularity.orchestrator", "label": "Singularity"},
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "last_stats": result.scout_stats if result else None,
            "opportunities": {
                "total": len(self.opportunities),
                "long": sum(
                    1
                    for o in self.opportunities
                    if o.action in (SignalAction.BUY, SignalAction.WATCH)
                ),
                "short": sum(1 for o in self.opportunities if o.action == SignalAction.SELL),
            },
        }

    async def scan(self) -> list[Opportunity]:
        result = await self.run_pipeline()
        return result.opportunities

    async def run_pipeline(self) -> AgentScanResult:
        logger.info("═══ ORCHESTRATOR: global multi-agent scan START ═══")
        now = datetime.now(timezone.utc)

        ath_date, ath_price, btc_price = await fetch_bitcoin_ath()
        self.alpha_model = analyze_bitcoin_cycle(ath_date, ath_price, btc_price)
        self.beta_model = analyze_presidential_cycle()

        watchlist = await get_watchlist(enabled_only=True)
        assets = [
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "asset_class": item["asset_class"],
                "source": item.get("source", "yahoo"),
            }
            for item in watchlist
        ]
        self.quotes = await fetch_quotes(assets)
        self._scouts = build_scout_roster(watchlist)

        long_scouts = [s for s in self._scouts if s.side == "long"]
        short_scouts = [s for s in self._scouts if s.side == "short"]
        assert len(long_scouts) == len(short_scouts), "LONG/SHORT scout parity required"

        # Parallel global hunt
        long_groups, short_groups = await asyncio.gather(
            asyncio.gather(
                *[
                    s.scout(self.quotes, alpha=self.alpha_model, beta=self.beta_model)
                    for s in long_scouts
                ]
            ),
            asyncio.gather(
                *[
                    s.scout(self.quotes, alpha=self.alpha_model, beta=self.beta_model)
                    for s in short_scouts
                ]
            ),
        )

        long_findings: list[ScoutFinding] = [f for group in long_groups for f in group]
        short_findings: list[ScoutFinding] = [f for group in short_groups for f in group]

        # Specialists draw conclusions
        long_verdicts = self.long_specialist.evaluate(
            long_findings, alpha=self.alpha_model, beta=self.beta_model, now=now
        )
        short_verdicts = self.short_specialist.evaluate(
            short_findings, alpha=self.alpha_model, beta=self.beta_model, now=now
        )

        long_opps = self.long_specialist.to_opportunities(long_verdicts)
        short_opps = self.short_specialist.to_opportunities(short_verdicts)

        # Final developer: balanced merge (equal voice)
        opportunities = self._merge_balanced(long_opps, short_opps)
        self.opportunities = opportunities
        self.last_scan_at = now

        stats = {
            "long_scout_findings": len(long_findings),
            "short_scout_findings": len(short_findings),
            "long_accepted": len(long_opps),
            "short_accepted": len(short_opps),
            "merged": len(opportunities),
            "quotes": len(self.quotes),
            "scouts_long": len(long_scouts),
            "scouts_short": len(short_scouts),
            "per_scout_long": {s.scout_id: len(g) for s, g in zip(long_scouts, long_groups)},
            "per_scout_short": {s.scout_id: len(g) for s, g in zip(short_scouts, short_groups)},
        }

        self.last_result = AgentScanResult(
            opportunities=opportunities,
            long_findings=long_findings,
            short_findings=short_findings,
            long_verdicts=long_verdicts,
            short_verdicts=short_verdicts,
            alpha_model=self.alpha_model,
            beta_model=self.beta_model,
            quotes=self.quotes,
            scanned_at=now,
            scout_stats=stats,
        )
        logger.info(
            "═══ ORCHESTRATOR DONE: %d LONG + %d SHORT → %d merged ═══",
            len(long_opps),
            len(short_opps),
            len(opportunities),
        )
        return self.last_result

    @staticmethod
    def _merge_balanced(
        longs: list[Opportunity],
        shorts: list[Opportunity],
        *,
        per_side: int = 14,
    ) -> list[Opportunity]:
        longs = sorted(longs, key=lambda o: o.confidence, reverse=True)[:per_side]
        shorts = sorted(shorts, key=lambda o: o.confidence, reverse=True)[:per_side]
        # Interleave SHORT/LONG so neither side is buried
        merged: list[Opportunity] = []
        i = j = 0
        while i < len(shorts) or j < len(longs):
            if i < len(shorts):
                merged.append(shorts[i])
                i += 1
            if j < len(longs):
                merged.append(longs[j])
                j += 1
        # De-dupe by symbol preferring higher confidence
        best: dict[str, Opportunity] = {}
        for o in merged:
            prev = best.get(o.symbol)
            if not prev or o.confidence > prev.confidence:
                best[o.symbol] = o
        # Preserve interleave order
        ordered = []
        seen: set[str] = set()
        for o in merged:
            if o.symbol in seen:
                continue
            ordered.append(best[o.symbol])
            seen.add(o.symbol)
        return ordered

    def agent_report(self) -> dict[str, Any]:
        """Full war-room report for API/UI."""
        status = self.roster_status()
        result = self.last_result
        if not result:
            return {**status, "ready": False}
        return {
            **status,
            "ready": True,
            "long_verdicts": [
                {
                    "symbol": v.symbol,
                    "name": v.name,
                    "accepted": v.accepted,
                    "confidence": v.confidence,
                    "summary": v.summary,
                    "scout_ids": v.scout_ids,
                    "factors": v.factors,
                }
                for v in result.long_verdicts
            ],
            "short_verdicts": [
                {
                    "symbol": v.symbol,
                    "name": v.name,
                    "accepted": v.accepted,
                    "confidence": v.confidence,
                    "summary": v.summary,
                    "scout_ids": v.scout_ids,
                    "factors": v.factors,
                }
                for v in result.short_verdicts
            ],
            "long_findings_sample": [
                {
                    "scout_id": f.scout_id,
                    "symbol": f.symbol,
                    "confidence": f.confidence,
                    "rationale": f.rationale,
                }
                for f in result.long_findings[:20]
            ],
            "short_findings_sample": [
                {
                    "scout_id": f.scout_id,
                    "symbol": f.symbol,
                    "confidence": f.confidence,
                    "rationale": f.rationale,
                }
                for f in result.short_findings[:20]
            ],
        }


orchestrator = AgentOrchestrator()
