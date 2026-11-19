"""Mark open positions at the sell quote. Snapshot on every close and every minute."""

from __future__ import annotations

from app.solana_desk.execution import simulate_sell
from app.solana_desk.models import finite
from app.solana_desk.quotes import SOL_MINT, QuoteRouter, QuoteUnavailable
from app.solana_desk.store import insert_equity, latest_equity


async def mark_positions(rows: list[dict], router: QuoteRouter, sol_usd: float, settings: dict) -> tuple[float, str]:
    """Return (open value in SOL, fill source). Model is used only when both venues are down."""
    total = 0.0
    source = "quote"
    for row in rows:
        if row.get("status") != "open":
            continue
        atoms = str(row.get("token_atoms") or "")
        if atoms.isdigit() and int(atoms) > 0:
            try:
                quote = await router.quote(
                    input_mint=str(row["mint"]),
                    output_mint=SOL_MINT,
                    amount=int(atoms),
                    slippage_bps=int(round(min(3.0, finite(settings.get("max_slippage_pct"), 2.0)) * 100)),
                )
                total += quote.out_amount / 1_000_000_000
                continue
            except QuoteUnavailable:
                source = "model"
        paper = simulate_sell(
            next_price=finite(row.get("last_price")),
            tokens=finite(row.get("tokens")),
            sol_usd=sol_usd,
            liquidity_usd=finite(row.get("liquidity_usd")),
            priority_fee_sol=finite(settings.get("priority_fee_sol"), 0.00005),
            pump_fee_rate=finite(settings.get("pump_fee_rate"), 0.01),
            slippage_base_bps=finite(settings.get("slippage_base_bps"), 50),
        )
        total += paper.proceeds_sol
        source = "model"
    return total, source


async def snapshot(book: dict, rows: list[dict], router: QuoteRouter, reason: str) -> dict:
    settings = book.get("settings") or {}
    sol = finite(book.get("sol_usd"))
    open_value, source = await mark_positions(rows, router, sol, settings)
    cash = finite(book.get("cash_sol"))
    equity = cash + open_value
    await insert_equity(
        equity_sol=equity,
        equity_usd=equity * sol if sol else None,
        cash_sol=cash,
        open_value_sol=open_value,
        reason=f"{reason} · {source}",
    )
    peak = max(finite(book.get("peak_equity_sol")), equity)
    book["peak_equity_sol"] = peak
    if peak > 0:
        book["max_drawdown"] = max(finite(book.get("max_drawdown")), (peak - equity) / peak)
    drift = await live_drift(book, equity)
    return {"equity_sol": equity, "equity_usd": equity * sol, "open_value_sol": open_value, "source": source, "drift_pct": drift}


async def live_drift(book: dict, equity_sol: float) -> float | None:
    """Compare the book with the wallet. None when this process is not live."""
    from app.solana_desk.real_gate import gate_reason
    from app.solana_desk.db import read_armed

    if gate_reason(await read_armed()):
        return None
    wallet = book.get("wallet_sol")
    if wallet is None:
        return None
    if equity_sol <= 0:
        return None
    drift = abs(finite(wallet) - equity_sol) / equity_sol * 100
    book["equity_drift_pct"] = drift
    return drift


def session_window(now_oslo_hm: str, start: str, end: str) -> bool:
    """True when the clock sits inside the overnight window. Times are HH:MM."""
    def minutes(value: str) -> int:
        hour, minute = value.split(":")
        return int(hour) * 60 + int(minute)

    current = minutes(now_oslo_hm)
    begin = minutes(start)
    finish = minutes(end)
    if begin == finish:
        return True
    if begin < finish:
        return begin <= current < finish
    return current >= begin or current < finish


async def snapshot_age_seconds() -> float | None:
    row = await latest_equity()
    if not row:
        return None
    from datetime import datetime, timezone

    try:
        moment = datetime.fromisoformat(str(row["ts"]).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moment).total_seconds()
