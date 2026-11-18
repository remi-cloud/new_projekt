"""Paper fills: Solana fees, pump.fun fee, liquidity slippage, gap through the stop."""

from __future__ import annotations

from app.solana_desk.models import Fill, finite

LAMPORTS_PER_SOL = 1_000_000_000
BASE_SIGNATURE_LAMPORTS = 5_000
SLIPPAGE_CAP = 0.15


def network_fee_sol(priority_fee_sol: float) -> float:
    """Base signature fee plus an optional priority tip, both in SOL."""
    priority = max(0.0, finite(priority_fee_sol))
    return BASE_SIGNATURE_LAMPORTS / LAMPORTS_PER_SOL + priority


def slippage_rate(notional_usd: float, liquidity_usd: float, base_bps: float) -> float:
    """Constant-product style impact. Thin books slip more. Capped at 15%."""
    base = max(0.0, finite(base_bps)) / 10_000
    liq = max(finite(liquidity_usd), 1.0)
    impact = max(0.0, finite(notional_usd)) / (2.0 * liq)
    return min(SLIPPAGE_CAP, base + impact)


def simulate_buy(
    *,
    next_price: float,
    spend_sol: float,
    sol_usd: float,
    liquidity_usd: float,
    priority_fee_sol: float,
    pump_fee_rate: float,
    slippage_base_bps: float,
) -> Fill:
    """Buy fills at the next observed price, worsened by slippage. Fees come out of the spend."""
    price = finite(next_price)
    spend = finite(spend_sol)
    sol = finite(sol_usd)
    if price <= 0 or spend <= 0 or sol <= 0:
        raise ValueError("Brak ceny, budżetu albo kursu SOL.")
    notional = spend * sol
    slip = slippage_rate(notional, liquidity_usd, slippage_base_bps)
    fill_price = price * (1 + slip)
    network = network_fee_sol(priority_fee_sol)
    pump = spend * max(0.0, finite(pump_fee_rate))
    fee = network + pump
    cash_for_tokens = spend - fee
    if cash_for_tokens <= 0:
        raise ValueError("Opłaty zjadają całą pozycję.")
    tokens = (cash_for_tokens * sol) / fill_price
    return Fill(
        price=fill_price,
        tokens=tokens,
        debit_sol=spend,
        proceeds_sol=0.0,
        fee_sol=fee,
        network_fee_sol=network,
        pump_fee_sol=pump,
        slippage=slip,
    )


def simulate_sell(
    *,
    next_price: float,
    tokens: float,
    sol_usd: float,
    liquidity_usd: float,
    priority_fee_sol: float,
    pump_fee_rate: float,
    slippage_base_bps: float,
) -> Fill:
    """Sell fills at the next price, not at the stop level. A gap keeps the worse price."""
    price = finite(next_price)
    qty = finite(tokens)
    sol = finite(sol_usd)
    if price <= 0 or qty <= 0 or sol <= 0:
        raise ValueError("Brak ceny wyjścia albo ilości.")
    notional = qty * price
    slip = slippage_rate(notional, liquidity_usd, slippage_base_bps)
    fill_price = price * (1 - slip)
    gross = (qty * fill_price) / sol
    pump = gross * max(0.0, finite(pump_fee_rate))
    network = network_fee_sol(priority_fee_sol)
    fee = min(gross, pump + network)
    proceeds = max(0.0, gross - fee)
    return Fill(
        price=fill_price,
        tokens=qty,
        debit_sol=0.0,
        proceeds_sol=proceeds,
        fee_sol=fee,
        network_fee_sol=min(network, fee),
        pump_fee_sol=max(0.0, fee - min(network, fee)),
        slippage=slip,
    )


def stop_triggered(entry_price: float, seen_price: float, stop_pct: float) -> bool:
    entry = finite(entry_price)
    seen = finite(seen_price)
    if entry <= 0:
        return False
    return seen <= entry * (1 - max(0.0, finite(stop_pct)))
