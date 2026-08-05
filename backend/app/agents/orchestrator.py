"""
Singularity orchestrator — Kar Digital.

Uses Academy bitcoin/presidential cycles (adapted to Alpha/Beta scout shapes)
and MONITORED_ASSETS universe. Does not replace the Academy opportunity_scanner.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.scouts import ScoutAgent, build_scout_roster
from app.agents.specialists import LongSpecialist, ShortSpecialist
from app.agents.types import AgentScanResult, ScoutFinding
from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.model_adapters import bitcoin_as_alpha, presidential_as_beta
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.data.assets import MONITORED_ASSETS
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes
from app.data.whale_flows import fetch_whale_snapshot
from app.models.schemas import (
    AlphaModelStatus,
    AssetQuote,
    BetaModelStatus,
    Opportunity,
    SignalAction,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.opportunities: list[Opportunity] = []
        self.quotes: list[AssetQuote] = []
        self.alpha_model: AlphaModelStatus | None = None
        self.beta_model: BetaModelStatus | None = None
        self.last_result: AgentScanResult | None = None
        self.whale_by_symbol: dict[str, Any] = {}
        self._scouts: list[ScoutAgent] = []
        self.long_specialist = LongSpecialist()
        self.short_specialist = ShortSpecialist()

    def roster_status(self) -> dict[str, Any]:
        result = self.last_result
        long_scouts = [s for s in self._scouts if s.side == "long"]
        short_scouts = [s for s in self._scouts if s.side == "short"]
        return {
            "module": "Singularity",
            "brand": "Kar Digital",
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
        logger.info("═══ ORCHESTRATOR: Kar Digital Singularity START ═══")
        now = datetime.now(timezone.utc)

        ath_date, ath_price, btc_price = await fetch_bitcoin_ath()
        btc = analyze_bitcoin_cycle(ath_date, ath_price, btc_price)
        pres = analyze_presidential_cycle()
        self.alpha_model = bitcoin_as_alpha(btc)
        self.beta_model = presidential_as_beta(pres)

        assets = [
            {
                "symbol": a["symbol"],
                "name": a["name"],
                "asset_class": a["asset_class"],
                "source": a.get("source", "yahoo"),
            }
            for a in MONITORED_ASSETS
        ]
        crypto_syms = [
            a["symbol"].upper()
            for a in assets
            if str(a.get("asset_class", "")).lower() == "crypto"
        ]
        self.quotes, self.whale_by_symbol = await asyncio.gather(
            fetch_quotes(),
            fetch_whale_snapshot(crypto_syms or None),
        )
        self._scouts = build_scout_roster(assets)

        long_scouts = [s for s in self._scouts if s.side == "long"]
        short_scouts = [s for s in self._scouts if s.side == "short"]

        long_groups, short_groups = await asyncio.gather(
            asyncio.gather(
                *[
                    s.scout(
                        self.quotes,
                        alpha=self.alpha_model,
                        beta=self.beta_model,
                        whale_by_symbol=self.whale_by_symbol,
                    )
                    for s in long_scouts
                ]
            ),
            asyncio.gather(
                *[
                    s.scout(
                        self.quotes,
                        alpha=self.alpha_model,
                        beta=self.beta_model,
                        whale_by_symbol=self.whale_by_symbol,
                    )
                    for s in short_scouts
                ]
            ),
        )

        long_findings: list[ScoutFinding] = [f for group in long_groups for f in group]
        short_findings: list[ScoutFinding] = [f for group in short_groups for f in group]

        long_verdicts = self.long_specialist.evaluate(
            long_findings, alpha=self.alpha_model, beta=self.beta_model, now=now
        )
        short_verdicts = self.short_specialist.evaluate(
            short_findings, alpha=self.alpha_model, beta=self.beta_model, now=now
        )

        long_opps = self.long_specialist.to_opportunities(long_verdicts)
        short_opps = self.short_specialist.to_opportunities(short_verdicts)
        opportunities = self._merge_book(long_opps, short_opps, quotes=self.quotes)
        self.opportunities = opportunities
        self.last_scan_at = now

        stats = {
            "long_scout_findings": len(long_findings),
            "short_scout_findings": len(short_findings),
            "long_accepted": len(long_opps),
            "short_accepted": len(short_opps),
            "merged": len(opportunities),
            "merged_long": sum(
                1
                for o in opportunities
                if o.action in (SignalAction.BUY, SignalAction.WATCH)
            ),
            "merged_short": sum(1 for o in opportunities if o.action == SignalAction.SELL),
            "quotes": len(self.quotes),
            "scouts_long": len(long_scouts),
            "scouts_short": len(short_scouts),
            "whale_symbols": len(self.whale_by_symbol),
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
    def _resolve_side_conflict(
        long_o: Opportunity | None,
        short_o: Opportunity | None,
        chg7: float | None,
    ) -> Opportunity | None:
        if long_o and not short_o:
            return long_o
        if short_o and not long_o:
            return short_o
        if not long_o and not short_o:
            return None
        assert long_o is not None and short_o is not None

        if chg7 is not None:
            if chg7 >= 1.0:
                winner, note = long_o, f"Konflikt LONG/SHORT → trend 7d {chg7:+.1f}% wygrywa LONG"
            elif chg7 <= -1.5:
                winner, note = short_o, f"Konflikt LONG/SHORT → trend 7d {chg7:+.1f}% wygrywa SHORT"
            elif long_o.confidence >= short_o.confidence + 5:
                winner, note = long_o, "Konflikt LONG/SHORT → wyższa pewność LONG"
            elif short_o.confidence >= long_o.confidence + 5:
                winner, note = short_o, "Konflikt LONG/SHORT → wyższa pewność SHORT"
            else:
                return None
        else:
            winner = long_o if long_o.confidence >= short_o.confidence else short_o
            note = "Konflikt LONG/SHORT → wyższa pewność (brak 7d)"

        return winner.model_copy(update={"rationale": f"{winner.rationale} | {note}"})

    def _merge_book(
        self,
        longs: list[Opportunity],
        shorts: list[Opportunity],
        *,
        quotes: list[AssetQuote] | None = None,
        max_total: int = 28,
        min_confidence: float = 55.0,
    ) -> list[Opportunity]:
        chg7_map = {q.symbol.upper(): q.change_pct_7d for q in (quotes or [])}
        quality_long = sorted(
            (o for o in longs if o.confidence >= min_confidence),
            key=lambda o: o.confidence,
            reverse=True,
        )
        quality_short = sorted(
            (o for o in shorts if o.confidence >= min_confidence),
            key=lambda o: o.confidence,
            reverse=True,
        )

        by_sym: dict[str, dict[str, Opportunity]] = {}
        for o in quality_long:
            by_sym.setdefault(o.symbol.upper(), {})["long"] = o
        for o in quality_short:
            by_sym.setdefault(o.symbol.upper(), {})["short"] = o

        resolved: list[Opportunity] = []
        for sym, sides in by_sym.items():
            picked = self._resolve_side_conflict(
                sides.get("long"),
                sides.get("short"),
                chg7_map.get(sym),
            )
            if picked:
                resolved.append(picked)

        resolved.sort(key=lambda o: o.confidence, reverse=True)
        return resolved[:max_total]

    def agent_report(self) -> dict[str, Any]:
        status = self.roster_status()
        result = self.last_result
        if not result:
            return {**status, "ready": False}
        return {
            **status,
            "ready": True,
            "whale_flows": self.whale_by_symbol,
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
