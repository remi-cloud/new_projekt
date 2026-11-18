"""Position, daily-loss and kill-switch gates for the paper book."""

from __future__ import annotations

from app.solana_desk.models import finite


def opening_block(
    *,
    kill_switch: bool,
    running: bool,
    size_sol: float,
    cash_sol: float,
    reserved_sol: float,
    day_pnl_sol: float,
    open_count: int,
    settings: dict,
) -> str:
    """Empty string means a new paper entry is allowed."""
    if kill_switch:
        return "wyłącznik awaryjny"
    if not running:
        return "biurko zatrzymane"
    size = finite(size_sol)
    if size <= 0:
        return "pusty rozmiar pozycji"
    max_trade = finite(settings.get("max_per_trade_sol"), 0.1)
    if size > max_trade + 1e-12:
        return "limit na transakcję"
    available = finite(cash_sol) - finite(reserved_sol)
    if size > available + 1e-12:
        return "brak wolnego SOL"
    loss_cap = finite(settings.get("daily_loss_sol"), 0.2)
    if finite(day_pnl_sol) <= -loss_cap:
        return "dzienny limit straty"
    if open_count >= int(finite(settings.get("max_open"), 3)):
        return "limit otwartych pozycji"
    return ""
