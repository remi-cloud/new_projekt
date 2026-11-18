"""Kill switch, per-trade cap, cash and the daily loss limit."""

from app.solana_desk.limits import opening_block
from app.solana_desk.models import DEFAULT_SETTINGS


def _gate(**overrides) -> str:
    base = dict(
        kill_switch=False,
        running=True,
        size_sol=0.05,
        cash_sol=1,
        reserved_sol=0,
        day_pnl_sol=0,
        open_count=0,
        settings=dict(DEFAULT_SETTINGS),
    )
    base.update(overrides)
    return opening_block(**base)


def test_a_normal_entry_is_allowed():
    assert _gate() == ""


def test_kill_switch_blocks_before_size():
    assert _gate(kill_switch=True) == "wyłącznik awaryjny"


def test_stopped_desk_blocks():
    assert _gate(running=False) == "biurko zatrzymane"


def test_trade_cap_cash_daily_loss_and_open_slots():
    assert _gate(size_sol=0.2) == "limit na transakcję"
    assert _gate(size_sol=0.05, cash_sol=0.04) == "brak wolnego SOL"
    assert _gate(size_sol=0.05, cash_sol=1, reserved_sol=0.97) == "brak wolnego SOL"
    assert _gate(day_pnl_sol=-0.2) == "dzienny limit straty"
    assert _gate(day_pnl_sol=-0.19) == ""
    assert _gate(open_count=3) == "limit otwartych pozycji"


def test_real_caps_and_reserve():
    from app.solana_desk.limits import cap_block, live_buy_block

    assert cap_block(slippage_bps=50, priority_fee_sol=0.00005, settings=DEFAULT_SETTINGS) == ""
    assert cap_block(slippage_bps=250, priority_fee_sol=0.00005, settings=DEFAULT_SETTINGS) == "limit poślizgu"
    assert cap_block(slippage_bps=50, priority_fee_sol=0.02, settings=DEFAULT_SETTINGS) == "limit opłaty priorytetowej"
    common = dict(
        slippage_bps=50,
        priority_fee_sol=0.00005,
        balance_sol=1,
        reserve_sol=0.05,
        size_sol=0.05,
        cash_sol=1,
        reserved_sol=0,
        day_pnl_sol=0,
        open_count=0,
        running=True,
        kill_switch=False,
        settings=dict(DEFAULT_SETTINGS),
    )
    assert live_buy_block(**common) == ""
    assert live_buy_block(**{**common, "balance_sol": 0.08}) == "rezerwa portfela"
    assert live_buy_block(**{**common, "kill_switch": True}) == "wyłącznik awaryjny"
    assert live_buy_block(**{**common, "day_pnl_sol": -0.2}) == "dzienny limit straty"
    assert live_buy_block(**{**common, "open_count": 3}) == "limit otwartych pozycji"
