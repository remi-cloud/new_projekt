"""Collect trade signal candidates from opportunities and pearl finds."""

from __future__ import annotations

from app.ai.pearl_hunter.service import list_pearl_finds
from app.config import settings
from app.db.database import get_recent_opportunities
from app.execution.models import SignalCandidate
from app.scanners.opportunity_scanner import scanner


def _dedupe_key(c: SignalCandidate) -> str:
    return c.symbol.upper()


async def collect_signal_candidates(min_confidence: float | None = None) -> list[SignalCandidate]:
    min_conf = min_confidence if min_confidence is not None else settings.execution_min_confidence
    pearl_min = settings.pearl_min_score
    seen: set[str] = set()
    out: list[SignalCandidate] = []

    # Live scanner opportunities (in-memory, freshest)
    for opp in scanner.opportunities or []:
        if opp.action.value != "buy" and str(opp.action) != "buy":
            continue
        if opp.confidence < min_conf:
            continue
        key = opp.symbol.upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            SignalCandidate(
                symbol=opp.symbol,
                name=opp.name,
                asset_class=opp.asset_class.value if hasattr(opp.asset_class, "value") else str(opp.asset_class),
                region=_region_for_symbol(opp.symbol),
                source="opportunity",
                confidence=opp.confidence,
                price=opp.price,
                rationale=opp.rationale,
            )
        )

    # DB fallback if scanner empty
    if not out:
        rows = await get_recent_opportunities(limit=80)
        for row in rows:
            if row.get("action") != "buy":
                continue
            conf = float(row.get("confidence") or 0)
            if conf < min_conf:
                continue
            sym = row["symbol"]
            key = sym.upper()
            if key in seen:
                continue
            seen.add(key)
            out.append(
                SignalCandidate(
                    symbol=sym,
                    name=row.get("name") or sym,
                    asset_class=row.get("asset_class") or "stock",
                    region=_region_for_symbol(sym),
                    source="opportunity",
                    confidence=conf,
                    price=float(row.get("price") or 0),
                    rationale=row.get("rationale") or "",
                )
            )

    pearls = await list_pearl_finds(limit=60)
    for row in pearls:
        score = float(row.get("score") or row.get("confidence") or 0)
        if score < pearl_min:
            continue
        sym = row["symbol"]
        key = sym.upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            SignalCandidate(
                symbol=sym,
                name=row.get("name") or sym,
                asset_class=row.get("asset_class") or "stock",
                region=row.get("region") or _region_for_symbol(sym),
                source="pearl",
                confidence=score,
                price=float(row.get("price") or 0),
                rationale=row.get("rationale") or "",
            )
        )

    return out


def _region_for_symbol(symbol: str) -> str:
    if symbol.endswith(".WA"):
        return "pl"
    if symbol.endswith("-USD"):
        return "global"
    for assessment in scanner.market_assessments or []:
        if assessment.symbol == symbol:
            return assessment.region.value if hasattr(assessment.region, "value") else str(assessment.region)
    return "global"
