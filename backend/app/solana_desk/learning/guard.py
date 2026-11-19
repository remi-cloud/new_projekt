"""A lesson may only make a rule stricter. Loosening is stored as rejected."""

from __future__ import annotations

from app.solana_desk.learning.dsl import AGENT_ACTIONS, FEATURES, RUG_PARAMS
from app.solana_desk.models import finite

_FORBIDDEN = {
    "SOLANA_REAL_TRADING",
    "SOLANA_BOT_PRIVATE_KEY",
    "SOLANA_RPC_URL",
    "kill_switch",
    "real_trading",
    "private_key",
    "rpc_url",
}

# Higher is looser for these settings.
_LOWER_IS_STRICTER = {
    "max_slippage_pct",
    "max_slippage_bps",
    "max_size_pct",
    "max_per_trade_sol",
    "max_open",
    "daily_loss_sol",
    "max_top10_pct",
    "max_top_holder_pct",
    "max_dev_pct",
    "max_tax_pct",
    "max_age_hours",
}
# Higher is stricter.
_HIGHER_IS_STRICTER = {
    "min_liquidity_usd",
    "min_lp_locked_pct",
    "min_age_minutes",
    "min_reserve_sol",
    "min_volume_usd",
    "priority_fee_sol",
    "stop_pct",
}


def validate(agent: str, rule: dict, settings: dict | None = None) -> tuple[bool, str]:
    """Return (ok, reason). ok is false when the rule would loosen a limit."""
    settings = settings or {}
    action = rule.get("action") or {}
    kind = str(action.get("type") or "")
    param = str(action.get("param") or "")
    allowed = AGENT_ACTIONS.get(agent)
    if allowed is None:
        return False, "unknown agent"
    if kind not in allowed:
        return False, f"{agent} cannot {kind}"
    blob = f"{param} {action}".lower()
    for word in _FORBIDDEN:
        if word.lower() in blob:
            return False, f"refused field {word}"
    if "disable" in blob or param in {"enabled", "check_enabled"} or action.get("value") == "disable":
        return False, "cannot disable a check"
    for cond in rule.get("when") or []:
        if cond.get("feature") not in FEATURES:
            return False, "unknown feature"
    if kind == "scale_size":
        factor = finite(action.get("factor"), 1)
        if factor > 1:
            return False, "scale_size factor > 1"
        if factor <= 0:
            return False, "scale_size factor empty"
        return True, ""
    if kind == "delay_entry":
        seconds = finite(action.get("value"), 0)
        if seconds < 0 or seconds > 120:
            return False, "delay out of range"
        return True, ""
    if kind in {"block", "require_check"}:
        return True, ""
    if kind != "tighten_param":
        return False, "unknown action"
    if agent == "rug_check" and param not in RUG_PARAMS:
        return False, f"rug param {param} is not whitelisted"
    value = action.get("value")
    if value is None:
        return False, "tighten needs a value"
    number = finite(value)
    if param == "priority_fee_sol" and number > 0.01:
        return False, "priority fee above 0.01 SOL"
    if param in {"max_slippage_pct", "max_slippage_bps"} and number > 3 and param.endswith("pct"):
        return False, "slippage cap above 3%"
    if param == "max_slippage_bps" and number > 300:
        return False, "slippage cap above 3%"
    current = settings.get(param)
    if current is None:
        return True, ""
    current_n = finite(current)
    if param in _LOWER_IS_STRICTER and number > current_n + 1e-12:
        return False, f"{param} would loosen"
    if param in _HIGHER_IS_STRICTER and number < current_n - 1e-12:
        return False, f"{param} would loosen"
    return True, ""
