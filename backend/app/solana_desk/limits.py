"""Position, daily-loss, reserve and fee caps for paper and real sends."""

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


def cap_block(*, slippage_bps: float, priority_fee_sol: float, settings: dict) -> str:
    """Hard caps. A value above the cap aborts the send instead of being clipped."""
    max_slip = finite(settings.get("max_slippage_bps"), 100)
    if finite(slippage_bps) > min(max_slip, 300) or finite(slippage_bps) <= 0:
        return "limit poślizgu"
    if finite(priority_fee_sol) > 0.01 or finite(priority_fee_sol) < 0:
        return "limit opłaty priorytetowej"
    return ""


def live_buy_block(
    *,
    slippage_bps: float,
    priority_fee_sol: float,
    balance_sol: float,
    reserve_sol: float,
    size_sol: float,
    cash_sol: float,
    reserved_sol: float,
    day_pnl_sol: float,
    open_count: int,
    running: bool,
    kill_switch: bool,
    settings: dict,
) -> str:
    capped = cap_block(
        slippage_bps=slippage_bps,
        priority_fee_sol=priority_fee_sol,
        settings=settings,
    )
    if capped:
        return capped
    if finite(balance_sol) - finite(size_sol) < finite(reserve_sol) - 1e-12:
        return "rezerwa portfela"
    return opening_block(
        kill_switch=kill_switch,
        running=running,
        size_sol=size_sol,
        cash_sol=cash_sol,
        reserved_sol=reserved_sol,
        day_pnl_sol=day_pnl_sol,
        open_count=open_count,
        settings=settings,
    )
