import logging
from datetime import datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.presidential_cycle import (
    analyze_presidential_cycle,
    presidential_buy_weight,
    presidential_sell_weight,
)
from app.data.market_data import fetch_bitcoin_ath, fetch_quotes
from app.db.settings_store import get_watchlist
from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    BetaModelStatus,
    Opportunity,
    SignalAction,
)

logger = logging.getLogger(__name__)


class OpportunityScanner:
    def __init__(self) -> None:
        self.last_scan_at: datetime | None = None
        self.opportunities: list[Opportunity] = []
        self.alpha_model: AlphaModelStatus | None = None
        self.beta_model: BetaModelStatus | None = None
        self.quotes: list[AssetQuote] = []

    # Compatibility aliases used by a few call sites
    @property
    def bitcoin_cycle(self) -> AlphaModelStatus | None:
        return self.alpha_model

    @property
    def presidential_cycle(self) -> BetaModelStatus | None:
        return self.beta_model

    async def scan(self) -> list[Opportunity]:
        logger.info("Starting market scan (global LONG+SHORT)...")
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

        buy_w = presidential_buy_weight()
        sell_w = presidential_sell_weight()
        opportunities: list[Opportunity] = []
        now = datetime.now(timezone.utc)

        for quote in self.quotes:
            opp = self._evaluate_asset(quote, buy_w, sell_w, now)
            if opp:
                opportunities.append(opp)

        opportunities.sort(key=lambda o: o.confidence, reverse=True)
        self.opportunities = opportunities
        self.last_scan_at = now
        n_long = sum(1 for o in opportunities if o.action in (SignalAction.BUY, SignalAction.WATCH))
        n_short = sum(1 for o in opportunities if o.action == SignalAction.SELL)
        logger.info(
            "Scan complete: %d opportunities (%d LONG-bias, %d SHORT)",
            len(opportunities),
            n_long,
            n_short,
        )
        return opportunities

    def _evaluate_asset(
        self,
        quote: AssetQuote,
        buy_w: float,
        sell_w: float,
        now: datetime,
    ) -> Opportunity | None:
        if quote.asset_class == AssetClass.CRYPTO:
            return self._evaluate_crypto(quote, now)
        return self._evaluate_traditional(quote, buy_w, sell_w, now)

    def _evaluate_crypto(self, quote: AssetQuote, now: datetime) -> Opportunity | None:
        if not self.alpha_model:
            return None

        cycle = self.alpha_model
        chg7 = quote.change_pct_7d
        chg24 = quote.change_pct_24h

        if cycle.phase.value == "bear":
            if cycle.signal == SignalAction.SELL:
                confidence = 58 + (100 - cycle.phase_progress_pct) * 0.2
                if chg7 is not None and chg7 < -5:
                    confidence += 10  # momentum confirms SHORT
                if chg24 is not None and chg24 < -3:
                    confidence += 4
                rationale = (
                    f"Model Alpha · wczesny spadek ({cycle.days_since_reference}d). "
                    f"{cycle.rationale}"
                )
                return self._make_opp(
                    quote, SignalAction.SELL, confidence, "alpha", "bear", rationale, now
                )
            if cycle.signal == SignalAction.WATCH:
                # Mid bear: SHORT if still dumping hard, else soft LONG watch
                if chg7 is not None and chg7 < -8:
                    return self._make_opp(
                        quote,
                        SignalAction.SELL,
                        62 + min(abs(chg7), 15),
                        "alpha",
                        "bear",
                        f"Model Alpha · kontynuacja spadku 7d {chg7:+.1f}%. {cycle.rationale}",
                        now,
                    )
                return self._make_opp(
                    quote,
                    SignalAction.WATCH,
                    52,
                    "alpha",
                    "bear",
                    f"Model Alpha · obserwacja. {cycle.rationale}",
                    now,
                )
            if cycle.signal == SignalAction.BUY:
                confidence = 50 + cycle.phase_progress_pct * 0.3
                if chg7 is not None and chg7 < -5:
                    confidence += 10
                rationale = (
                    f"Model Alpha · faza {cycle.phase.value} ({cycle.days_since_reference}d). "
                    f"{cycle.rationale}"
                )
                return self._make_opp(
                    quote, SignalAction.BUY, confidence, "alpha", cycle.phase.value, rationale, now
                )

        elif cycle.phase.value == "bull":
            if cycle.signal == SignalAction.BUY:
                confidence = 65 + (100 - cycle.phase_progress_pct) * 0.2
                # Extreme melt-up → tactical SHORT overlay
                if chg7 is not None and chg7 > 12:
                    return self._make_opp(
                        quote,
                        SignalAction.SELL,
                        60 + min(chg7, 20) * 0.5,
                        "alpha",
                        "bull",
                        f"Model Alpha · przegrzanie 7d {chg7:+.1f}% — taktyczny SHORT. {cycle.rationale}",
                        now,
                    )
                return self._make_opp(
                    quote,
                    SignalAction.BUY,
                    confidence,
                    "alpha",
                    "bull",
                    f"Model Alpha · fala wzrostowa. {cycle.rationale}",
                    now,
                )
            if cycle.signal == SignalAction.HOLD:
                if chg7 is not None and chg7 > 10:
                    return self._make_opp(
                        quote,
                        SignalAction.SELL,
                        58,
                        "alpha",
                        "bull",
                        f"Model Alpha · hold + przegrzanie 7d {chg7:+.1f}% → SHORT. {cycle.rationale}",
                        now,
                    )
                return self._make_opp(
                    quote,
                    SignalAction.HOLD,
                    55,
                    "alpha",
                    "bull",
                    f"Model Alpha · utrzymuj pozycje. {cycle.rationale}",
                    now,
                )

        elif cycle.phase.value == "distribution":
            return self._make_opp(
                quote,
                SignalAction.SELL,
                70,
                "alpha",
                "distribution",
                f"Model Alpha · dystrybucja. {cycle.rationale}",
                now,
            )

        return None

    def _evaluate_traditional(
        self,
        quote: AssetQuote,
        buy_w: float,
        sell_w: float,
        now: datetime,
    ) -> Opportunity | None:
        """Global scan for indexes/stocks/bonds/commodities/forex — LONG and SHORT."""
        if not self.beta_model:
            return None

        beta = self.beta_model
        phase_key = beta.current_phase.value
        phase_n = beta.phase_number
        prior = beta.signal
        chg7 = quote.change_pct_7d
        chg24 = quote.change_pct_24h

        class_modifier = {
            AssetClass.INDEX: 1.05,
            AssetClass.STOCK: 1.0,
            AssetClass.BOND: self._bond_modifier(phase_n),
            AssetClass.COMMODITY: self._commodity_modifier(phase_n),
            AssetClass.FOREX: 0.85,
        }.get(quote.asset_class, 0.85)

        # Start from phase prior; confidence uses the matching side weight
        action = prior
        if prior == SignalAction.SELL:
            confidence = 42 + sell_w * 42 * class_modifier
        elif prior == SignalAction.BUY:
            confidence = 42 + buy_w * 42 * class_modifier
        elif prior == SignalAction.WATCH:
            # Mixed regime — lean toward the stronger phase weight
            if sell_w >= buy_w:
                action = SignalAction.SELL
                confidence = 40 + sell_w * 36 * class_modifier
            else:
                action = SignalAction.BUY
                confidence = 40 + buy_w * 36 * class_modifier
        else:  # HOLD
            confidence = 48 * class_modifier
            action = SignalAction.HOLD

        # ── Per-asset momentum (indexes / stocks / etc.) ───────────────
        # Weak regimes (phase 1–2 or prior SELL): fade rallies → SHORT
        weak_regime = phase_n in (1, 2) or prior == SignalAction.SELL
        strong_regime = phase_n == 3 or prior == SignalAction.BUY

        if quote.asset_class in (
            AssetClass.INDEX,
            AssetClass.STOCK,
            AssetClass.COMMODITY,
            AssetClass.FOREX,
        ):
            if weak_regime:
                if chg7 is not None and chg7 >= 2.0:
                    action = SignalAction.SELL
                    confidence = 55 + min(chg7, 12) * 1.8 * class_modifier
                elif chg7 is not None and chg7 <= -5.0:
                    # Deep dump in weak phase → bounce LONG (not empty SHORT-only)
                    action = SignalAction.BUY
                    confidence = 52 + min(abs(chg7), 12) * 1.2 * class_modifier
                elif chg24 is not None and chg24 >= 1.5 and action != SignalAction.BUY:
                    action = SignalAction.SELL
                    confidence = max(confidence, 54 + chg24 * 2)
                elif action == SignalAction.HOLD:
                    action = SignalAction.SELL
                    confidence = max(confidence, 50 + sell_w * 20)
            elif strong_regime:
                if chg7 is not None and chg7 <= -3.0:
                    action = SignalAction.BUY
                    confidence = 55 + min(abs(chg7), 12) * 1.5 * class_modifier
                elif chg7 is not None and chg7 >= 8.0:
                    # Melt-up → tactical SHORT even in bull regime
                    action = SignalAction.SELL
                    confidence = 56 + min(chg7 - 8, 10) * 1.5
                elif action == SignalAction.HOLD:
                    action = SignalAction.BUY
                    confidence = max(confidence, 52 + buy_w * 20)
            else:
                # Phase 4 / mixed HOLD-WATCH
                if chg7 is not None and chg7 >= 3.5:
                    action = SignalAction.SELL
                    confidence = 54 + min(chg7, 10) * 1.4
                elif chg7 is not None and chg7 <= -3.5:
                    action = SignalAction.BUY
                    confidence = 54 + min(abs(chg7), 10) * 1.4

        # Bonds: often inverse hedge — LONG bonds when equities short-biased
        if quote.asset_class == AssetClass.BOND:
            if phase_n in (1, 2) or prior == SignalAction.SELL:
                action = SignalAction.BUY
                confidence = 55 + sell_w * 25 * class_modifier
                if chg7 is not None and chg7 < -2:
                    confidence += 8  # dip in bonds during risk-off
            elif phase_n == 3:
                if chg7 is not None and chg7 > 2:
                    action = SignalAction.SELL
                    confidence = 52 + chg7 * 2
                else:
                    action = SignalAction.HOLD
                    confidence = 48
            elif phase_n == 4 and (chg7 is not None and chg7 > 1.5):
                action = SignalAction.SELL
                confidence = 53

        # Index / stock boosts by phase (both sides)
        if quote.asset_class in (AssetClass.STOCK, AssetClass.INDEX):
            if phase_n == 3 and action == SignalAction.BUY:
                confidence += 12
            if phase_n in (1, 2) and action == SignalAction.SELL:
                confidence += 12

        if confidence < 45:
            return None
        # Drop pure HOLD from actionable feed (super/okazje want KUP/SPRZEDAJ)
        if action == SignalAction.HOLD:
            return None

        side_pl = {
            SignalAction.BUY: "LONG",
            SignalAction.SELL: "SHORT",
            SignalAction.WATCH: "LONG (słaby)",
        }.get(action, action.value)

        rationale = (
            f"Model Beta · {phase_key.replace('phase_', 'faza ')} → {side_pl}. "
            f"{beta.historical_bias}."
        )
        if chg7 is not None:
            rationale += f" Zmiana 7d: {chg7:+.1f}%."
        if chg24 is not None:
            rationale += f" 24h: {chg24:+.1f}%."

        return self._make_opp(
            quote, action, min(confidence, 95), "beta", phase_key, rationale, now
        )

    @staticmethod
    def _bond_modifier(phase_number: int) -> float:
        return {1: 1.1, 2: 1.2, 3: 0.7, 4: 0.9}.get(phase_number, 0.8)

    @staticmethod
    def _commodity_modifier(phase_number: int) -> float:
        return {1: 0.9, 2: 1.0, 3: 1.1, 4: 0.95}.get(phase_number, 0.9)

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
