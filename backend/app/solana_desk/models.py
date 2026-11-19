"""Shared types for the Solana Desk paper book."""

from __future__ import annotations

from dataclasses import dataclass, field


def finite(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return number


@dataclass(frozen=True)
class TokenView:
    """One Solana mint as the agents see it."""

    mint: str
    symbol: str
    name: str = ""
    price_usd: float = 0.0
    liquidity_usd: float = 0.0
    volume_usd: float = 0.0
    age_minutes: float = 0.0
    venue: str = "pump"
    mint_authority_active: bool | None = None
    freeze_authority_active: bool | None = None
    top_holder_pct: float | None = None
    top10_holder_pct: float | None = None
    dev_holder_pct: float | None = None
    buy_tax_pct: float | None = None
    sell_tax_pct: float | None = None
    can_sell: bool | None = None
    change_5m_pct: float | None = None
    rugged: bool = False
    risk_ready: bool = False
    spike: float | None = None
    buys_pct: float | None = None
    lp_locked_pct: float | None = None
    volume_5m_usd: float | None = None
    creator: str = ""
    transfer_fee_bps: float | None = None
    permanent_delegate: bool | None = None
    non_transferable: bool | None = None
    onchain_ready: bool = False


@dataclass
class MarketSnapshot:
    sol_usd: float
    discovered: list[TokenView] = field(default_factory=list)
    quotes: dict[str, TokenView] = field(default_factory=dict)
    error: str = ""
    risk_pending: int = 0


@dataclass(frozen=True)
class Fill:
    price: float
    tokens: float
    debit_sol: float
    proceeds_sol: float
    fee_sol: float
    network_fee_sol: float
    pump_fee_sol: float
    slippage: float


@dataclass(frozen=True)
class RiskVerdict:
    ok: bool
    reasons: tuple[str, ...]


DEFAULT_SETTINGS: dict[str, float | int | str] = {
    "starting_sol": 1.0,
    "position_sol": 0.05,
    "max_per_trade_sol": 0.1,
    "daily_loss_sol": 0.2,
    "stop_pct": 0.06,
    "take_profit_pct": 0.25,
    "trail_activate_pct": 0.12,
    "trail_gap_pct": 0.08,
    "time_stop_minutes": 30,
    "max_open": 3,
    "min_liquidity_usd": 1500.0,
    "min_age_minutes": 2.0,
    "max_age_hours": 72.0,
    "min_volume_usd": 400.0,
    "max_top_holder_pct": 30.0,
    "max_top10_pct": 70.0,
    "max_dev_pct": 10.0,
    "max_tax_pct": 10.0,
    "priority_fee_sol": 0.00005,
    "pump_fee_rate": 0.01,
    "slippage_base_bps": 50.0,
    "max_slippage_bps": 100.0,
    "min_reserve_sol": 0.05,
    "rugcheck_top_n": 15,
    # Equity sizing. position_sol is deprecated and is not used to size a trade.
    "risk_per_trade_pct": 0.015,
    "min_size_pct": 0.05,
    "max_size_pct": 0.40,
    "max_slippage_pct": 2.0,
    "session_start": "23:00",
    "session_end": "07:00",
}


def fresh_agents() -> dict[str, dict[str, float | int | str]]:
    return {
        "scout": {"seen": 0, "note": "Czeka na pierwszy obieg."},
        "checker": {
            "passed": 0,
            "rejected": 0,
            "pending_risk": 0,
            "note": "Czeka na kandydatów.",
            "reasons": {},
        },
        "sniper": {"entries": 0, "skipped": 0, "note": "Bez wejść."},
        "exit": {"exits": 0, "note": "Bez wyjść."},
    }


def fresh_book() -> dict:
    return {
        "running": True,
        "kill_switch": False,
        "cash_sol": 1.0,
        "starting_sol": 1.0,
        "peak_equity_sol": 1.0,
        "max_drawdown": 0.0,
        "realized_pnl_sol": 0.0,
        "fees_sol": 0.0,
        "day_key": "",
        "day_start_equity_sol": 1.0,
        "sol_usd": 0.0,
        "last_tick_at": "",
        "last_error": "",
        "worker_owner": "",
        "worker_expires": 0.0,
        "closed_trades": 0,
        "wins": 0,
        "losses": 0,
        "settings": dict(DEFAULT_SETTINGS),
        "agents": fresh_agents(),
    }
