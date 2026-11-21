import asyncio
import logging
from datetime import datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.regional_macro import REGION_LABELS, build_regional_cycles_snapshot
from app.data.assets import MONITORED_ASSETS
from app.data.fast_quotes import fetch_fast_quotes
from app.data.market_data import (
    fetch_bitcoin_ath,
    fetch_bitcoin_ath_yahoo,
    fetch_btc_cycle_low,
    fetch_quotes_with_stats,
)
from app.models.schemas import (
    AssetClass,
    AssetCycleAssessment,
    AssetQuote,
    BitcoinCycleStatus,
    MarketSummary,
    Opportunity,
    RegionalCycleSnapshot,
)
from app.scanners.asset_analyzer import analyzer, build_market_summary

logger = logging.getLogger(__name__)

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}
# BTC price older than this is shown with a "stale" flag (and its real timestamp).
BTC_STALE_AFTER_S = 15 * 60


class OpportunityScanner:
    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.last_price_tick_at: datetime | None = None
        self.live_mode: bool = False
        self.opportunities: list[Opportunity] = []
        self.market_assessments: list[AssetCycleAssessment] = []
        self.market_summary: MarketSummary | None = None
        self.bitcoin_cycle: BitcoinCycleStatus | None = None
        self.regional_cycles: list[RegionalCycleSnapshot] = []
        self.quotes: list[AssetQuote] = []
        self._price_stats: dict[str, dict] = {}
        self.scan_in_progress: bool = False
        self._scan_lock = asyncio.Lock()
        # Real BTC cycle inputs with provenance (source, fetched_at)
        self._btc_ath: tuple | None = None  # (date, price, source, fetched_at)
        self._btc_price: tuple | None = None  # (price, source, fetched_at)
        self._btc_low: tuple | None = None  # (price, date, for_ath_date)

    async def refresh_bitcoin_inputs(self) -> None:
        """Fetch ATH + price (CoinGecko, Yahoo as second real source) and the post-ATH low."""
        now = datetime.now(timezone.utc)
        try:
            ath_date, ath_price, px = await fetch_bitcoin_ath()
            src = "CoinGecko"
        except Exception as exc:
            logger.warning("CoinGecko BTC ATH failed (%s) — trying Yahoo", exc)
            try:
                ath_date, ath_price, px = await fetch_bitcoin_ath_yahoo()
                src = "Yahoo Finance"
            except Exception as exc2:
                logger.warning("Yahoo BTC ATH failed too: %s", exc2)
                if self._btc_ath is None:
                    raise RuntimeError("Brak danych BTC (CoinGecko i Yahoo niedostępne)") from exc2
                self._rebuild_bitcoin_cycle()  # last real values, now flagged stale
                return
        self._btc_ath = (ath_date, float(ath_price), src, now)
        self._btc_price = (float(px), src, now)
        try:
            low_px, low_date = await fetch_btc_cycle_low(ath_date)
            if low_px:
                self._btc_low = (float(low_px), low_date, ath_date)
        except Exception as exc:
            logger.warning("BTC cycle low fetch failed: %s", exc)
            if self._btc_low and self._btc_low[2] != ath_date:
                self._btc_low = None
        self._rebuild_bitcoin_cycle()

    def _rebuild_bitcoin_cycle(self) -> None:
        if not self._btc_ath or not self._btc_price:
            return
        ath_date, ath_price, ath_src, ath_at = self._btc_ath
        px, px_src, px_at = self._btc_price
        today = datetime.now(timezone.utc).date()
        if px > ath_price:  # live price above the stored ATH → a new ATH today
            ath_date, ath_price, ath_src, ath_at = today, px, px_src, px_at
            self._btc_ath = (ath_date, ath_price, ath_src, ath_at)
            self._btc_low = None
        low = self._btc_low if self._btc_low and self._btc_low[2] == ath_date else None
        if low and px < low[0]:
            low = (px, today, ath_date)
            self._btc_low = low
        status = analyze_bitcoin_cycle(
            ath_date,
            ath_price,
            px,
            as_of=today,
            cycle_low_price=low[0] if low else None,
            cycle_low_date=low[1] if low else None,
        )
        now = datetime.now(timezone.utc)
        stale = (now - px_at).total_seconds() > BTC_STALE_AFTER_S
        self.bitcoin_cycle = status.model_copy(
            update={
                "price_source": px_src,
                "price_updated_at": px_at,
                "ath_source": ath_src,
                "ath_updated_at": ath_at,
                "stale": stale,
            }
        )

    async def scan(self, *, force: bool = False) -> list[Opportunity]:
        """Run a full market scan. Concurrent callers wait for the in-flight scan
        instead of returning empty results (which previously wiped the Markets UI).
        """
        async with self._scan_lock:
            if (
                not force
                and self.market_assessments
                and self.bitcoin_cycle
            ):
                return self.opportunities

            self.scan_in_progress = True
            try:
                return await self._run_scan()
            finally:
                self.scan_in_progress = False

    async def _run_scan(self) -> list[Opportunity]:
        logger.info("Starting full market scan (%d assets)...", len(MONITORED_ASSETS))
        await self.refresh_bitcoin_inputs()
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
        if self.scan_in_progress:
            return {"updated": 0, "full_scan": False, "deferred": True}
        if not self.bitcoin_cycle or not self._price_stats:
            await self.scan()
            return {"updated": len(self.quotes), "full_scan": True}

        fast = await fetch_fast_quotes()
        if not fast:
            return {"updated": 0, "full_scan": False}

        from app.paper.pricing import merge_fast_quotes

        merge_fast_quotes(fast)
        updated = len(fast)
        btc = fast.get("BTC-USD")
        if btc is not None and btc.price and btc.price > 0:
            self._btc_price = (float(btc.price), "Yahoo Finance (spot)", btc.updated_at)
        self._rebuild_bitcoin_cycle()  # days since ATH + price stay current every tick

        self._reassess()
        self.last_price_tick_at = datetime.now(timezone.utc)
        self.live_mode = True
        return {"updated": updated, "full_scan": False}

    def _reassess(self) -> None:
        if not self.bitcoin_cycle:
            return

        self.market_assessments = analyzer.assess_all(
            self.quotes,
            ASSET_MAP,
            self.bitcoin_cycle,
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
        self.opportunities.sort(
            key=lambda o: (o.is_momentum_pick, o.confidence),
            reverse=True,
        )

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
            momentum_score=a.momentum_score,
            momentum_signal=a.momentum_signal,
            is_momentum_pick=a.is_momentum_pick,
            rationale=a.rationale,
            created_at=now,
            community=a.community,
        )


scanner = OpportunityScanner()
