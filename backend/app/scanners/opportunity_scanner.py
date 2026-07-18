import logging
from datetime import datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import analyze_presidential_cycle, presidential_buy_weight
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes
from app.models.schemas import (
    AssetClass,
    AssetQuote,
    BitcoinCycleStatus,
    Opportunity,
    PresidentialCycleStatus,
    SignalAction,
)

logger = logging.getLogger(__name__)


class OpportunityScanner:
    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.opportunities: list[Opportunity] = []
        self.bitcoin_cycle: BitcoinCycleStatus | None = None
        self.presidential_cycle: PresidentialCycleStatus | None = None
        self.quotes: list[AssetQuote] = []

    async def scan(self) -> list[Opportunity]:
        logger.info("Starting market scan...")
        ath_date, ath_price, btc_price = await fetch_bitcoin_ath()
        self.bitcoin_cycle = analyze_bitcoin_cycle(ath_date, ath_price, btc_price)
        self.presidential_cycle = analyze_presidential_cycle()
        self.quotes = await fetch_quotes()

        pres_weight = presidential_buy_weight()
        opportunities: list[Opportunity] = []
        now = datetime.now(timezone.utc)

        for quote in self.quotes:
            opp = self._evaluate_asset(quote, pres_weight, now)
            if opp:
                opportunities.append(opp)

        opportunities.sort(key=lambda o: o.confidence, reverse=True)
        self.opportunities = opportunities
        self.last_scan_at = now
        logger.info("Scan complete: %d opportunities found", len(opportunities))
        return opportunities

    def _evaluate_asset(
        self, quote: AssetQuote, pres_weight: float, now: datetime
    ) -> Opportunity | None:
        if quote.asset_class == AssetClass.CRYPTO:
            return self._evaluate_crypto(quote, now)
        return self._evaluate_traditional(quote, pres_weight, now)

    def _evaluate_crypto(self, quote: AssetQuote, now: datetime) -> Opportunity | None:
        if not self.bitcoin_cycle:
            return None

        cycle = self.bitcoin_cycle
        base_confidence = 50.0

        if cycle.phase.value == "bear":
            if cycle.signal in (SignalAction.BUY, SignalAction.WATCH):
                action = SignalAction.BUY if cycle.signal == SignalAction.BUY else SignalAction.WATCH
                confidence = base_confidence + cycle.phase_progress_pct * 0.3
                if quote.change_pct_7d and quote.change_pct_7d < -5:
                    confidence += 10
                rationale = (
                    f"Cykl BTC: {cycle.phase.value} ({cycle.days_since_ath}d od ATH). "
                    f"{cycle.rationale}"
                )
                return self._make_opp(quote, action, confidence, "bitcoin_cycle", cycle.phase.value, rationale, now)

        elif cycle.phase.value == "bull":
            if cycle.signal == SignalAction.BUY:
                action = SignalAction.BUY
                confidence = 65 + (100 - cycle.phase_progress_pct) * 0.2
                rationale = f"Cykl BTC: fala wzrostowa. {cycle.rationale}"
                return self._make_opp(quote, action, confidence, "bitcoin_cycle", "bull", rationale, now)
            elif cycle.signal == SignalAction.HOLD:
                return self._make_opp(
                    quote, SignalAction.HOLD, 55, "bitcoin_cycle", "bull",
                    f"Cykl BTC: utrzymuj pozycje. {cycle.rationale}", now,
                )

        elif cycle.phase.value == "distribution":
            return self._make_opp(
                quote, SignalAction.SELL, 70, "bitcoin_cycle", "distribution",
                f"Cykl BTC: faza dystrybucji. {cycle.rationale}", now,
            )

        return None

    def _evaluate_traditional(
        self, quote: AssetQuote, pres_weight: float, now: datetime
    ) -> Opportunity | None:
        if not self.presidential_cycle:
            return None

        pres = self.presidential_cycle
        year_key = pres.current_year.value

        # Asset-class adjustments within presidential cycle
        class_modifier = {
            AssetClass.INDEX: 1.0,
            AssetClass.STOCK: 0.95,
            AssetClass.BOND: self._bond_modifier(pres.year_number),
            AssetClass.COMMODITY: self._commodity_modifier(pres.year_number),
            AssetClass.FOREX: 0.7,
        }.get(quote.asset_class, 0.8)

        confidence = 40 + pres_weight * 40 * class_modifier

        if pres.signal == SignalAction.BUY:
            action = SignalAction.BUY
            if quote.change_pct_7d and quote.change_pct_7d < -3:
                confidence += 8
        elif pres.signal == SignalAction.WATCH:
            action = SignalAction.WATCH
            confidence -= 10
        elif pres.signal == SignalAction.HOLD:
            action = SignalAction.HOLD
        else:
            action = SignalAction.SELL
            confidence -= 20

        # Year 2 midterm: bonds often outperform — flip for bonds
        if quote.asset_class == AssetClass.BOND and pres.year_number == 2:
            action = SignalAction.BUY
            confidence += 15

        # Year 3: strongest for equities
        if quote.asset_class in (AssetClass.STOCK, AssetClass.INDEX) and pres.year_number == 3:
            confidence += 12

        if confidence < 45:
            return None

        rationale = (
            f"Cykl prezydencki: {year_key.replace('_', ' ')} ({pres.president}). "
            f"{pres.historical_bias}."
        )
        if quote.change_pct_7d is not None:
            rationale += f" Zmiana 7d: {quote.change_pct_7d:+.1f}%."

        return self._make_opp(
            quote, action, min(confidence, 95), "presidential_cycle", year_key, rationale, now
        )

    @staticmethod
    def _bond_modifier(year_number: int) -> float:
        # Bonds tend to do well in year 2 (flight to safety) and year 1 weakness
        return {1: 0.9, 2: 1.2, 3: 0.6, 4: 0.8}.get(year_number, 0.8)

    @staticmethod
    def _commodity_modifier(year_number: int) -> float:
        return {1: 0.8, 2: 1.0, 3: 1.1, 4: 0.9}.get(year_number, 0.9)

    @staticmethod
    def _make_opp(
        quote: AssetQuote,
        action: SignalAction,
        confidence: float,
        cycle_source: str,
        phase: str,
        rationale: str,
        now: datetime,
    ) -> Opportunity:
        return Opportunity(
            symbol=quote.symbol,
            name=quote.name,
            asset_class=quote.asset_class,
            action=action,
            confidence=round(confidence, 1),
            cycle_source=cycle_source,
            phase=phase,
            price=quote.price,
            rationale=rationale,
            created_at=now,
        )


scanner = OpportunityScanner()
