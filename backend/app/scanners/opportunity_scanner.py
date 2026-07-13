import logging
from datetime import datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle
from app.cycles.regional_macro import REGION_LABELS, build_regional_cycles_snapshot
from app.data.assets import MONITORED_ASSETS
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes_with_stats
from app.models.schemas import (
    AssetClass,
    AssetCycleAssessment,
    BitcoinCycleStatus,
    MarketSummary,
    Opportunity,
    PresidentialCycleStatus,
    RegionalCycleSnapshot,
    SignalAction,
)
from app.scanners.asset_analyzer import analyzer, build_market_summary

logger = logging.getLogger(__name__)

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}


class OpportunityScanner:
    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.opportunities: list[Opportunity] = []
        self.market_assessments: list[AssetCycleAssessment] = []
        self.market_summary: MarketSummary | None = None
        self.bitcoin_cycle: BitcoinCycleStatus | None = None
        self.presidential_cycle: PresidentialCycleStatus | None = None
        self.regional_cycles: list[RegionalCycleSnapshot] = []
        self.quotes: list = []

    async def scan(self) -> list[Opportunity]:
        logger.info("Starting global market scan (%d assets)...", len(MONITORED_ASSETS))
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
        self.quotes, price_stats = await fetch_quotes_with_stats()

        self.market_assessments = analyzer.assess_all(
            self.quotes,
            ASSET_MAP,
            self.bitcoin_cycle,
            self.presidential_cycle,
            price_stats,
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

        self.last_scan_at = now
        logger.info(
            "Scan complete: %d/%d assets, %d opportunities",
            len(self.quotes),
            len(MONITORED_ASSETS),
            len(self.opportunities),
        )
        return self.opportunities

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
