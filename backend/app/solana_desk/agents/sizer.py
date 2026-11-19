"""Size from equity. A fixed ticket is not a decision."""

from __future__ import annotations

from dataclasses import dataclass

from app.solana_desk.learning.apply import effects_for, reason_for
from app.solana_desk.models import finite
from app.solana_desk.quotes import SOL_MINT, QuoteRouter, QuoteUnavailable


class SizeRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class SizePlan:
    pct: float
    size_sol: float
    size_usd: float
    reason: str
    impact_pct: float
    quotes: int
    inputs: dict


def base_pct(settings: dict) -> float:
    risk = finite(settings.get("risk_per_trade_pct"), 0.015)
    stop = finite(settings.get("stop_pct"), 0.06) or 0.06
    lo = finite(settings.get("min_size_pct"), 0.05)
    hi = finite(settings.get("max_size_pct"), 0.40)
    return min(hi, max(lo, risk / stop))


async def plan(
    *,
    equity_sol: float,
    cash_sol: float,
    reserved_sol: float,
    sol_usd: float,
    mint: str,
    settings: dict,
    router: QuoteRouter,
    features: dict | None = None,
) -> SizePlan | None:
    """Return None when nothing tradable fits the caps. Never returns position_sol."""
    feats = dict(features or {})
    pct = base_pct(settings)
    hi = finite(settings.get("max_size_pct"), 0.40)
    effects = await effects_for("sizer", feats)
    notes: list[str] = []
    for effect in effects:
        if effect.type == "scale_size" and effect.factor:
            pct *= float(effect.factor)
            notes.append(f"lesson #{effect.lesson_id} ×{effect.factor}")
        if effect.type == "tighten_param" and effect.param == "max_size_pct" and effect.value is not None:
            hi = min(hi, float(effect.value))
            pct = min(pct, hi)
            notes.append(f"lesson #{effect.lesson_id} max {hi:.0%}")
    pct = min(pct, hi)
    equity = finite(equity_sol)
    size = equity * pct
    free = finite(cash_sol) - finite(reserved_sol) - finite(settings.get("min_reserve_sol"), 0.05)
    hard = finite(settings.get("max_per_trade_sol"), 0.1)
    size = min(size, free, hard)
    if size <= 0 or equity <= 0:
        raise SizeRejected("brak wolnego SOL")
    cap = min(3.0, finite(settings.get("max_slippage_pct"), 2.0))
    bps = int(round(cap * 100))
    try:
        fitted, impact, quotes = await _fit(router, mint, size, cap, bps)
    except QuoteUnavailable as exc:
        raise SizeRejected(str(exc)) from exc
    if fitted is None or fitted <= 0:
        raise SizeRejected(f"slippage est {impact:.2f}% > cap {cap:.1f}%")
    pct_out = fitted / equity if equity else 0
    usd = fitted * finite(sol_usd)
    base = f"{pct_out:.0%} of equity"
    reason = reason_for(effects, base) if notes else base
    if impact > 0:
        reason = f"{reason} · impact {impact:.2f}%"
    return SizePlan(
        pct=pct_out,
        size_sol=fitted,
        size_usd=usd,
        reason=reason,
        impact_pct=impact,
        quotes=quotes,
        inputs={
            "risk_per_trade_pct": finite(settings.get("risk_per_trade_pct"), 0.015),
            "stop_pct": finite(settings.get("stop_pct"), 0.06),
            "min_size_pct": finite(settings.get("min_size_pct"), 0.05),
            "max_size_pct": hi,
            "equity_sol": equity,
            "free_sol": free,
            "max_per_trade_sol": hard,
        },
    )


async def _fit(router: QuoteRouter, mint: str, size_sol: float, cap: float, bps: int) -> tuple[float | None, float, int]:
    lo = 0.0
    hi = size_sol
    best: float | None = None
    impact = 0.0
    quotes = 0
    guess = size_sol
    for _ in range(4):
        lamports = max(1, int(guess * 1_000_000_000))
        try:
            quote = await router.quote(input_mint=SOL_MINT, output_mint=mint, amount=lamports, slippage_bps=bps)
        except QuoteUnavailable:
            raise
        quotes += 1
        impact = quote.impact_pct
        if impact <= cap + 1e-9:
            best = guess
            if guess >= size_sol * 0.999:
                break
            lo = guess
        else:
            hi = guess
        if quotes >= 4:
            break
        guess = (lo + hi) / 2
        if hi - lo < size_sol * 0.05:
            break
    return best, impact, quotes
