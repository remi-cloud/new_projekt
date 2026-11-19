"""Whitelisted lesson rule. Unknown features and actions are rejected."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

FEATURES = frozenset(
    {
        "spike",
        "buys_pct",
        "lp_locked_pct",
        "top1_pct",
        "top10_pct",
        "dev_pct",
        "age_minutes",
        "liquidity_usd",
        "volume_usd",
        "quote_impact_pct",
        "priority_fee_sol",
        "latency_ms",
        "size_sol",
        "size_pct",
        "pnl_sol",
        "stop_pct",
        "slip_pct",
        "drift_pct",
        "mark_gap_pct",
        "reason_len",
        "confirm_failed",
        "fade_pct",
    }
)

ACTIONS = frozenset({"block", "tighten_param", "scale_size", "delay_entry", "require_check"})
OPS = frozenset({">=", ">", "<=", "<", "==", "!="})

AGENT_ACTIONS = {
    "scanner": frozenset({"block", "require_check"}),
    "rug_check": frozenset({"block", "tighten_param"}),
    "sizer": frozenset({"scale_size", "tighten_param"}),
    "executor": frozenset({"tighten_param", "delay_entry"}),
    "equity": frozenset({"require_check"}),
    "logger": frozenset({"require_check"}),
    "llm": frozenset({"require_check", "block"}),
}

RUG_PARAMS = frozenset(
    {"min_liquidity_usd", "max_top10_pct", "max_top_holder_pct", "max_dev_pct", "min_lp_locked_pct", "min_age_minutes"}
)


class When(BaseModel):
    feature: str
    op: str
    value: float


class Action(BaseModel):
    type: str
    param: str | None = None
    value: float | None = None
    factor: float | None = None


class Rule(BaseModel):
    when: list[When] = Field(default_factory=list)
    action: Action


class Proposal(BaseModel):
    agent: str
    diagnosis: str = ""
    lesson_text: str
    rule: Rule
    confidence: float = 0.5


def parse_proposal(payload: Any) -> Proposal:
    if isinstance(payload, str):
        import json

        payload = json.loads(payload)
    try:
        proposal = Proposal.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    if proposal.rule.action.type not in ACTIONS:
        raise ValueError("unknown action")
    for cond in proposal.rule.when:
        if cond.feature not in FEATURES or cond.op not in OPS:
            raise ValueError(f"unknown feature or op: {cond.feature} {cond.op}")
    return proposal


def matches(rule: dict, features: dict) -> bool:
    for cond in rule.get("when") or []:
        feature = cond.get("feature")
        if feature not in FEATURES:
            return False
        if feature not in features or features.get(feature) is None:
            return False
        if not _cmp(float(features[feature]), str(cond.get("op")), float(cond.get("value"))):
            return False
    return True


def _cmp(left: float, op: str, right: float) -> bool:
    if op == ">=":
        return left >= right
    if op == ">":
        return left > right
    if op == "<=":
        return left <= right
    if op == "<":
        return left < right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    return False


def rule_key(rule: dict) -> str:
    import hashlib
    import json

    blob = json.dumps(rule, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
