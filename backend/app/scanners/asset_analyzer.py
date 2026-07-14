"""Combined cyclical assessment per asset."""

from datetime import datetime, timezone

from app.cycles.bitcoin_cycle import analyze_bitcoin_cycle
from app.cycles.macro_types import MacroCycleResult
from app.cycles.momentum_cycle import analyze_momentum, momentum_aligns_with_cycle
from app.cycles.price_cycle import analyze_price_cycle
from app.cycles.regional_macro import analyze_regional_macro, macro_weight_for_region
from app.models.schemas import (
    AssetClass,
    AssetCycleAssessment,
    AssetQuote,
    BitcoinCycleStatus,
    CyclePhase,
    PresidentialCycleStatus,
    SignalAction,
)

SIGNAL_PRIORITY = {
    SignalAction.BUY: 4,
    SignalAction.WATCH: 3,
    SignalAction.HOLD: 2,
    SignalAction.SELL: 1,
}

# Base split: regional macro vs price cycle vs momentum.
PRICE_CYCLE_WEIGHT = 0.35
MOMENTUM_WEIGHT = 0.25


def _combine_three_signals(
    macro_signal: SignalAction,
    macro_conf: float,
    price_signal: SignalAction,
    price_conf: float,
    momentum_signal: SignalAction,
    momentum_conf: float,
    region: str = "global",
) -> tuple[SignalAction, float, bool]:
    """
    Weight macro + price cycle + momentum.
    Returns (final_signal, confidence, is_momentum_pick).
    """
    macro_w = macro_weight_for_region(region) * 0.85
    price_w = PRICE_CYCLE_WEIGHT
    mom_w = MOMENTUM_WEIGHT

    cycle_signal, cycle_conf = _combine_signals(
        macro_signal, macro_conf, price_signal, price_conf, region=region
    )

    if _signals_conflict(cycle_signal, momentum_signal):
        mom_w *= 0.40
    divisor = macro_w + price_w + mom_w
    macro_w /= divisor
    price_w /= divisor
    mom_w /= divisor

    scores = {SignalAction.BUY: 0.0, SignalAction.WATCH: 0.0, SignalAction.HOLD: 0.0, SignalAction.SELL: 0.0}
    weights = {SignalAction.BUY: 1.0, SignalAction.WATCH: 0.5, SignalAction.HOLD: 0.2, SignalAction.SELL: -0.6}

    for sig, conf, w in [
        (cycle_signal, cycle_conf, macro_w + price_w),
        (momentum_signal, momentum_conf, mom_w),
    ]:
        for action in scores:
            if action == sig:
                scores[action] += conf * w
            elif weights[action] * weights[sig] > 0:
                scores[action] += conf * w * 0.3

    best = max(scores, key=lambda s: scores[s])
    combined_conf = min(95, max(35, scores[best]))

    aligned = momentum_aligns_with_cycle(momentum_signal, cycle_signal)
    is_pick = False

    if aligned and momentum_conf >= 55:
        combined_conf = min(95, combined_conf + 8)
        if best in (SignalAction.BUY, SignalAction.SELL) and momentum_signal == best:
            is_pick = True
            combined_conf = min(95, combined_conf + 5)

    if _signals_conflict(best, momentum_signal) and momentum_conf >= 60:
        if best == SignalAction.BUY:
            best = SignalAction.WATCH
        elif best == SignalAction.SELL:
            best = SignalAction.WATCH
        combined_conf = max(35, combined_conf - 10)

    return best, combined_conf, is_pick


def _assess_momentum(stats: dict) -> tuple[SignalAction, float, str, float, str]:
    mom_sig, mom_conf, mom_phase, mom_score, mom_rat = analyze_momentum(stats)
    return mom_sig, mom_conf, mom_phase, mom_score, mom_rat


def _signals_conflict(a: SignalAction, b: SignalAction) -> bool:
    return (a, b) in {
        (SignalAction.BUY, SignalAction.SELL),
        (SignalAction.SELL, SignalAction.BUY),
    }


def _combine_signals(
    macro_signal: SignalAction,
    macro_conf: float,
    price_signal: SignalAction,
    price_conf: float,
    region: str = "global",
) -> tuple[SignalAction, float]:
    """Weight regional macro vs price cycle; dampen macro when price strongly disagrees."""
    macro_w = macro_weight_for_region(region)
    price_w = PRICE_CYCLE_WEIGHT

    if _signals_conflict(macro_signal, price_signal):
        macro_w *= 0.50
        price_w = 1.0 - macro_w
    else:
        total = macro_w + price_w
        macro_w /= total
        price_w /= total

    scores = {SignalAction.BUY: 0.0, SignalAction.WATCH: 0.0, SignalAction.HOLD: 0.0, SignalAction.SELL: 0.0}
    weights = {SignalAction.BUY: 1.0, SignalAction.WATCH: 0.5, SignalAction.HOLD: 0.2, SignalAction.SELL: -0.6}

    for sig, conf, w in [(macro_signal, macro_conf, macro_w), (price_signal, price_conf, price_w)]:
        for action in scores:
            if action == sig:
                scores[action] += conf * w
            elif weights[action] * weights[sig] > 0:
                scores[action] += conf * w * 0.3

    best = max(scores, key=lambda s: scores[s])
    combined_conf = min(95, max(35, scores[best]))
    return best, combined_conf


def _class_modifier(asset_class: AssetClass, macro: MacroCycleResult) -> float:
    if asset_class == AssetClass.INDEX:
        return 1.0
    if asset_class in (AssetClass.STOCK, AssetClass.ETF):
        return 0.95
    if asset_class == AssetClass.BOND:
        if macro.cycle_id == "presidential_cycle":
            year_hint = macro.phase
            bond_map = {"year_1": 0.9, "year_2": 1.2, "year_3": 0.6, "year_4": 0.8}
            return bond_map.get(year_hint, 0.85)
        return 0.90
    if asset_class == AssetClass.COMMODITY:
        return 0.92
    if asset_class == AssetClass.FOREX:
        return 0.75
    return 0.85


def _apply_traditional_adjustments(
    quote: AssetQuote,
    macro: MacroCycleResult,
    macro_sig: SignalAction,
    macro_conf: float,
    price_sig: SignalAction,
    price_conf: float,
) -> tuple[SignalAction, float, SignalAction, float]:
    """Asset-specific tweaks before signal combination."""
    if quote.asset_class == AssetClass.BOND and macro.cycle_id == "presidential_cycle":
        if macro.phase == "year_2":
            macro_sig = SignalAction.BUY
            macro_conf += 12

    if quote.asset_class in (AssetClass.INDEX, AssetClass.STOCK, AssetClass.ETF):
        if macro.cycle_id == "presidential_cycle" and macro.phase == "year_3":
            macro_conf += 10

    if quote.change_pct_7d is not None:
        if quote.change_pct_7d < -8 and price_sig == SignalAction.BUY:
            price_conf += 6
        elif quote.change_pct_7d > 12 and price_sig == SignalAction.SELL:
            price_conf += 8
        elif quote.change_pct_7d > 15 and macro_sig == SignalAction.BUY:
            macro_sig = SignalAction.WATCH
            macro_conf -= 5

    if quote.symbol == "^VIX":
        if price_sig == SignalAction.BUY:
            price_sig = SignalAction.SELL
        elif price_sig == SignalAction.SELL:
            price_sig = SignalAction.WATCH

    return macro_sig, macro_conf, price_sig, price_conf


class AssetAnalyzer:
    def assess_all(
        self,
        quotes: list[AssetQuote],
        asset_meta: dict[str, dict],
        bitcoin_cycle: BitcoinCycleStatus,
        presidential_cycle: PresidentialCycleStatus,
        price_stats: dict[str, dict],
    ) -> list[AssetCycleAssessment]:
        now = datetime.now(timezone.utc)
        assessments: list[AssetCycleAssessment] = []

        for quote in quotes:
            meta = asset_meta.get(quote.symbol, {})
            region = meta.get("region", "global")
            stats = price_stats.get(quote.symbol, {})

            if quote.asset_class == AssetClass.CRYPTO:
                a = self._assess_crypto(quote, region, bitcoin_cycle, stats, now)
            else:
                a = self._assess_traditional(quote, region, stats, now)
            if a:
                assessments.append(a)

        assessments.sort(key=lambda x: (x.is_momentum_pick, x.confidence), reverse=True)
        return assessments

    def _assess_crypto(
        self,
        quote: AssetQuote,
        region: str,
        btc_cycle: BitcoinCycleStatus,
        stats: dict,
        now: datetime,
    ) -> AssetCycleAssessment:
        high_52w = stats.get("high_52w")
        low_52w = stats.get("low_52w")

        price_phase, price_sig, price_conf, price_rat = analyze_price_cycle(
            quote.price, high_52w, low_52w
        )

        macro_phase = btc_cycle.phase
        macro_sig = btc_cycle.signal
        macro_conf = 50 + btc_cycle.phase_progress_pct * 0.3
        if quote.symbol == "BTC-USD":
            macro_conf = 60 + btc_cycle.phase_progress_pct * 0.35

        if quote.symbol != "BTC-USD" and quote.change_pct_7d is not None:
            if quote.change_pct_7d < -10 and macro_sig == SignalAction.BUY:
                price_conf += 8
            elif quote.change_pct_7d > 15 and macro_phase == CyclePhase.DISTRIBUTION:
                macro_sig = SignalAction.SELL

        mom_sig, mom_conf, mom_phase, mom_score, mom_rat = _assess_momentum(stats)

        final_sig, final_conf, is_pick = _combine_three_signals(
            macro_sig, macro_conf, price_sig, price_conf, mom_sig, mom_conf, region="global"
        )

        rationale = (
            f"[Cykl BTC: {macro_phase.value}, {btc_cycle.days_since_ath}d od ATH] "
            f"[Cena: {price_rat}] [Momentum: {mom_rat}]"
        )

        return AssetCycleAssessment(
            symbol=quote.symbol,
            name=quote.name,
            asset_class=quote.asset_class,
            region=region,
            price=quote.price,
            change_pct_24h=quote.change_pct_24h,
            change_pct_7d=quote.change_pct_7d,
            high_52w=high_52w,
            drawdown_from_high_pct=round(((high_52w - quote.price) / high_52w * 100), 1) if high_52w else None,
            macro_cycle="bitcoin_cycle",
            macro_phase=macro_phase.value,
            price_phase=price_phase.value,
            momentum_score=mom_score if stats.get("rsi_14") is not None else None,
            momentum_signal=mom_sig if stats.get("rsi_14") is not None else None,
            momentum_phase=mom_phase if stats.get("rsi_14") is not None else None,
            is_momentum_pick=is_pick,
            signal=final_sig,
            confidence=round(final_conf, 1),
            rationale=rationale,
            updated_at=now,
        )

    def _assess_traditional(
        self,
        quote: AssetQuote,
        region: str,
        stats: dict,
        now: datetime,
    ) -> AssetCycleAssessment:
        high_52w = stats.get("high_52w")
        low_52w = stats.get("low_52w")

        price_phase, price_sig, price_conf, price_rat = analyze_price_cycle(
            quote.price, high_52w, low_52w
        )

        macro = analyze_regional_macro(
            region=region,
            asset_class=quote.asset_class.value,
            symbol=quote.symbol,
            as_of=now.date(),
        )

        class_mod = _class_modifier(quote.asset_class, macro)
        macro_conf = macro.base_confidence * class_mod
        macro_sig = macro.signal
        macro_phase = macro.phase

        macro_sig, macro_conf, price_sig, price_conf = _apply_traditional_adjustments(
            quote, macro, macro_sig, macro_conf, price_sig, price_conf
        )

        mom_sig, mom_conf, mom_phase, mom_score, mom_rat = _assess_momentum(stats)

        final_sig, final_conf, is_pick = _combine_three_signals(
            macro_sig, macro_conf, price_sig, price_conf, mom_sig, mom_conf, region=region
        )

        cycle_label = {
            "presidential_cycle": "Cykl prez. USA",
            "polish_cycle": "Cykl PL",
            "europe_cycle": "Cykl EU",
            "asia_cycle": "Cykl Azja",
            "em_cycle": "Cykl EM",
            "global_commodity_cycle": "Cykl surowców",
            "global_forex_cycle": "Cykl forex",
            "global_macro_cycle": "Cykl globalny",
        }.get(macro.cycle_id, macro.cycle_id)

        rationale = f"[{cycle_label}: {macro_phase.replace('_', ' ')}] [Cena: {price_rat}] [Momentum: {mom_rat}]"
        if quote.change_pct_7d is not None:
            rationale += f" [7d: {quote.change_pct_7d:+.1f}%]"

        return AssetCycleAssessment(
            symbol=quote.symbol,
            name=quote.name,
            asset_class=quote.asset_class,
            region=region,
            price=quote.price,
            change_pct_24h=quote.change_pct_24h,
            change_pct_7d=quote.change_pct_7d,
            high_52w=high_52w,
            drawdown_from_high_pct=round(((high_52w - quote.price) / high_52w * 100), 1) if high_52w else None,
            macro_cycle=macro.cycle_id,
            macro_phase=macro_phase,
            price_phase=price_phase.value,
            momentum_score=mom_score if stats.get("rsi_14") is not None else None,
            momentum_signal=mom_sig if stats.get("rsi_14") is not None else None,
            momentum_phase=mom_phase if stats.get("rsi_14") is not None else None,
            is_momentum_pick=is_pick,
            signal=final_sig,
            confidence=round(final_conf, 1),
            rationale=rationale,
            updated_at=now,
        )


def build_market_summary(assessments: list[AssetCycleAssessment]) -> dict:
    by_signal: dict[str, int] = {}
    by_class: dict[str, int] = {}
    by_region: dict[str, int] = {}
    for a in assessments:
        by_signal[a.signal.value] = by_signal.get(a.signal.value, 0) + 1
        by_class[a.asset_class.value] = by_class.get(a.asset_class.value, 0) + 1
        by_region[a.region] = by_region.get(a.region, 0) + 1

    avg_conf = round(sum(a.confidence for a in assessments) / len(assessments), 1) if assessments else 0
    buy_count = by_signal.get("buy", 0)
    sell_count = by_signal.get("sell", 0)

    if buy_count > sell_count * 2:
        outlook = "bullish"
        outlook_label = "Przewaga sygnałów kupna — rynki w fazie akumulacji/wzrostu"
    elif sell_count > buy_count * 1.5:
        outlook = "bearish"
        outlook_label = "Przewaga sygnałów sprzedaży — ostrożność na szczytach"
    else:
        outlook = "mixed"
        outlook_label = "Mieszane sygnały — selektywne podejście do poszczególnych klas"

    return {
        "total_assets": len(assessments),
        "by_signal": by_signal,
        "by_class": by_class,
        "by_region": by_region,
        "avg_confidence": avg_conf,
        "outlook": outlook,
        "outlook_label": outlook_label,
    }


analyzer = AssetAnalyzer()
