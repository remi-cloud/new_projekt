import logging
from datetime import datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.cycles.regional_macro import REGION_LABELS, build_regional_cycles_snapshot
from app.data.assets import MONITORED_ASSETS
from app.data.fast_quotes import fetch_fast_quotes
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes_with_stats
from app.models.schemas import (
    AssetClass,
    AssetCycleAssessment,
    AssetQuote,
    BitcoinCycleStatus,
    MarketSummary,
    Opportunity,
    PresidentialCycleStatus,
    RegionalCycleSnapshot,
)
from app.scanners.asset_analyzer import analyzer, build_market_summary

logger = logging.getLogger(__name__)

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}


class OpportunityScanner:
    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.last_price_tick_at: datetime | None = None
        self.live_mode: bool = False
        self.opportunities: list[Opportunity] = []
        self.market_assessments: list[AssetCycleAssessment] = []
        self.market_summary: MarketSummary | None = None
        self.bitcoin_cycle: BitcoinCycleStatus | None = None
        self.presidential_cycle: PresidentialCycleStatus | None = None
        self.regional_cycles: list[RegionalCycleSnapshot] = []
        self.quotes: list[AssetQuote] = []
        self._price_stats: dict[str, dict] = {}

    async def scan(self) -> list[Opportunity]:
        logger.info("Starting full market scan (%d assets)...", len(MONITORED_ASSETS))
        ath_date, ath_price, btc_price = await fetch_bitcoin_ath()
        self.bitcoin_cycle = analyze_bitcoin_cycle(ath_date, ath_price, btc_price)
        self.presidential_cycle = analyze_presidential_cycle()
        snapshot = build_regional_cycles_snapshot()
        self.regional_cycles = [
            RegionalCycleSnapshot(
                region=region,
                region_label=REGION_LABELS.get(region, region),
                cycle_id=macro.cycle_id,
                phase=macro.phase,
                signal=macro.signal,
                buy_weight=round(macro.buy_weight, 2),
                bias=macro.bias,
                rationale=macro.rationale,
            )
            for region, macro in snapshot.items()
        ]
        self.quotes, self._price_stats = await fetch_quotes_with_stats()
        self._reassess()
        self.last_scan_at = datetime.now(timezone.utc)
        logger.info(
            "Full scan complete: %d/%d assets, %d opportunities",
            len(self.quotes),
            len(MONITORED_ASSETS),
            len(self.opportunities),
        )
        return self.opportunities

    async def price_tick(self) -> dict:
        """Lightweight real-time price refresh + signal re-evaluation."""
        if not self.bitcoin_cycle or not self._price_stats:
            await self.scan()
            return {"updated": len(self.quotes), "full_scan": True}

        fast = await fetch_fast_quotes()
        if not fast:
            return {"updated": 0, "full_scan": False}

        quote_map = {q.symbol: q for q in self.quotes}
        updated = 0
        for sym, new_q in fast.items():
            existing = quote_map.get(sym)
            if existing:
                existing.price = new_q.price
                existing.change_pct_24h = new_q.change_pct_24h or existing.change_pct_24h
                existing.updated_at = new_q.updated_at
                updated += 1
            else:
                self.quotes.append(new_q)
                updated += 1

        self._reassess()
        self.last_price_tick_at = datetime.now(timezone.utc)
        self.live_mode = True
        return {"updated": updated, "full_scan": False}

    def _reassess(self) -> None:
        if not self.bitcoin_cycle or not self.presidential_cycle:
            return

        self.market_assessments = analyzer.assess_all(
            self.quotes,
            ASSET_MAP,
            self.bitcoin_cycle,
            self.presidential_cycle,
            self._price_stats,
        )
        summary_dict = build_market_summary(self.market_assessments)
        self.market_summary = MarketSummary(**summary_dict)

        now = datetime.now(timezone.utc)
        self.opportunities = [
            self._assessment_to_opportunity(a, now)
            for a in self.market_assessments
            if a.confidence >= 50
        ]
        self.opportunities.sort(key=lambda o: o.confidence, reverse=True)

    @staticmethod
    def _assessment_to_opportunity(a: AssetCycleAssessment, now: datetime) -> Opportunity:
        return Opportunity(
            symbol=a.symbol,
            name=a.name,
            asset_class=a.asset_class,
            action=a.signal,
            confidence=a.confidence,
            cycle_source=a.macro_cycle,
            phase=f"{a.macro_phase}/{a.price_phase}",
            price=a.price,
            rationale=a.rationale,
            created_at=now,
        )


scanner = OpportunityScanner()
