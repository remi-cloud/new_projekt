"""Scout selection and exit rules. Checker and the fill math live next door."""

from __future__ import annotations

from datetime import datetime, timezone

from app.solana_desk.execution import stop_triggered
from app.solana_desk.models import TokenView, finite

_VENUES = {"pump", "pump_fun", "pumpswap", "raydium"}


def scout_select(tokens: list[TokenView]) -> list[TokenView]:
    """New pump mints and names that are still climbing on the curve or Raydium."""
    picked: list[TokenView] = []
    seen: set[str] = set()
    for token in tokens:
        mint = (token.mint or "").strip()
        if not mint or mint in seen:
            continue
        if token.venue not in _VENUES and not mint.endswith("pump"):
            continue
        if finite(token.price_usd) <= 0 and finite(token.liquidity_usd) <= 0 and not mint.endswith("pump"):
            continue
        age_hours = finite(token.age_minutes) / 60
        rising = finite(token.change_5m_pct) >= 5 or (
            token.venue in {"raydium", "pumpswap", "pump_fun"} and finite(token.change_5m_pct) >= 3
        )
        fresh = age_hours <= 72
        if not fresh and not rising:
            continue
        seen.add(mint)
        picked.append(token)
    return picked


def exit_reason(
    *,
    entry_price: float,
    seen_price: float,
    next_price: float,
    peak_price: float,
    opened_at: str,
    now: datetime,
    liquidity_usd: float,
    next_liquidity_usd: float,
    kill_switch: bool,
    settings: dict,
) -> str:
    """Return an exit code, or an empty string to hold."""
    if kill_switch:
        return "kill_switch"
    entry = finite(entry_price)
    seen = finite(seen_price) or entry
    nxt = finite(next_price)
    if entry <= 0 or nxt <= 0:
        return ""
    if finite(liquidity_usd) > 0 and finite(next_liquidity_usd) < finite(liquidity_usd) * 0.35:
        return "rug_gap"
    if nxt < seen * 0.55:
        return "rug_gap"
    stop_pct = finite(settings.get("stop_pct"), 0.06)
    if stop_triggered(entry, seen, stop_pct) or stop_triggered(entry, nxt, stop_pct):
        return "stop"
    peak = max(finite(peak_price), seen, nxt)
    activate = finite(settings.get("trail_activate_pct"), 0.12)
    gap = finite(settings.get("trail_gap_pct"), 0.08)
    if peak >= entry * (1 + activate) and nxt <= peak * (1 - gap):
        return "trailing"
    if nxt >= entry * (1 + finite(settings.get("take_profit_pct"), 0.25)):
        return "take_profit"
    minutes = finite(settings.get("time_stop_minutes"), 30)
    if minutes > 0 and opened_at:
        try:
            opened = datetime.fromisoformat(opened_at)
        except ValueError:
            opened = None
        if opened is not None:
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
            held = (now - opened).total_seconds() / 60
            if held >= minutes:
                return "time_stop"
    return ""


EXIT_TEXT = {
    "kill_switch": "wyłącznik awaryjny — wyjście po kolejnej cenie",
    "rug_gap": "rug / luka płynności — stop po realnej kolejnej cenie, nie po -6%",
    "stop": "stop -6% — wypełnienie po kolejnej cenie, z poślizgiem",
    "trailing": "trailing stop po szczycie",
    "take_profit": "take-profit",
    "time_stop": "time-stop",
}
