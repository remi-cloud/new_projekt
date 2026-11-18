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
