"""Fills charge network, priority and pump fees, and a stop keeps the gapped price."""

import pytest

from app.solana_desk.execution import simulate_buy, simulate_sell, slippage_rate, stop_triggered


def test_buy_charges_network_priority_pump_and_slippage():
    spend = 0.1
    sol_usd = 100
    liquidity = 10_000
    fill = simulate_buy(
        next_price=0.001,
        spend_sol=spend,
        sol_usd=sol_usd,
        liquidity_usd=liquidity,
        priority_fee_sol=0.00005,
        pump_fee_rate=0.01,
        slippage_base_bps=50,
    )
    slip = slippage_rate(spend * sol_usd, liquidity, 50)
    assert fill.slippage == pytest.approx(slip)
    assert fill.price == pytest.approx(0.001 * (1 + slip))
    assert fill.price > 0.001
    assert fill.network_fee_sol == pytest.approx(0.000005 + 0.00005)
    assert fill.pump_fee_sol == pytest.approx(0.001)
    assert fill.fee_sol == pytest.approx(fill.network_fee_sol + fill.pump_fee_sol)
    assert fill.debit_sol == pytest.approx(spend)
    assert fill.tokens > 0


def test_thin_book_slips_more_than_a_deep_one():
    deep = simulate_buy(
        next_price=1,
        spend_sol=0.2,
        sol_usd=100,
        liquidity_usd=500_000,
        priority_fee_sol=0,
        pump_fee_rate=0,
        slippage_base_bps=50,
    )
    thin = simulate_buy(
        next_price=1,
        spend_sol=0.2,
        sol_usd=100,
        liquidity_usd=400,
        priority_fee_sol=0,
        pump_fee_rate=0,
        slippage_base_bps=50,
    )
    assert thin.slippage > deep.slippage
    assert thin.price > deep.price
    assert thin.slippage <= 0.15


def test_stop_gap_fills_at_the_next_price_not_at_minus_six():
    entry = 1.0
    next_price = 0.40
    assert stop_triggered(entry, next_price, 0.06)
    fill = simulate_sell(
        next_price=next_price,
        tokens=100,
        sol_usd=100,
        liquidity_usd=5_000,
        priority_fee_sol=0.00005,
        pump_fee_rate=0.01,
        slippage_base_bps=50,
    )
    stop_price = entry * 0.94
    assert fill.price < next_price
    assert fill.price < stop_price
    assert fill.price == pytest.approx(next_price * (1 - fill.slippage))
    assert fill.fee_sol > 0
    assert fill.proceeds_sol > 0


def test_round_trip_at_the_same_price_loses_the_fees():
    buy = simulate_buy(
        next_price=1,
        spend_sol=0.1,
        sol_usd=100,
        liquidity_usd=20_000,
        priority_fee_sol=0.00005,
        pump_fee_rate=0.01,
        slippage_base_bps=50,
    )
    sell = simulate_sell(
        next_price=1,
        tokens=buy.tokens,
        sol_usd=100,
        liquidity_usd=20_000,
        priority_fee_sol=0.00005,
        pump_fee_rate=0.01,
        slippage_base_bps=50,
    )
    assert sell.proceeds_sol < buy.debit_sol
