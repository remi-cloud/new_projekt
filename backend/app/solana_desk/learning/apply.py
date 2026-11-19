"""Evaluate active lessons against the features of the decision in front of us."""

from __future__ import annotations

from dataclasses import dataclass

from app.solana_desk.learning.dsl import matches
from app.solana_desk.learning.memory import for_agent, maybe_promote_shadow, record_hit


@dataclass
class Effect:
    lesson_id: int
    type: str
    param: str
    value: float | None
    factor: float | None
    text: str


async def effects_for(agent: str, features: dict, *, decision_id: int | None = None) -> list[Effect]:
    """Hard limits are the caller's job. This only returns stricter lesson effects."""
    applied: list[Effect] = []
    for row in await for_agent(agent):
        rule = row.get("rule") or {}
        if not matches(rule, features):
            continue
        action = rule.get("action") or {}
        effect = Effect(
            lesson_id=int(row["id"]),
            type=str(action.get("type") or ""),
            param=str(action.get("param") or ""),
            value=action.get("value"),
            factor=action.get("factor"),
            text=str(row.get("lesson_text") or ""),
        )
        if row.get("status") == "shadow":
            await record_hit(
                effect.lesson_id,
                decision_id,
                "shadow",
                {"shadow": True, "would": effect.type, "features": features},
            )
            await maybe_promote_shadow(effect.lesson_id)
            continue
        name = {"block": "blocked", "scale_size": "scaled", "tighten_param": "tightened"}.get(effect.type, "tightened")
        if effect.type == "require_check":
            name = "tightened"
        if effect.type == "delay_entry":
            name = "tightened"
        await record_hit(effect.lesson_id, decision_id, name, {"features": features})
        applied.append(effect)
    return applied


def reason_for(effects: list[Effect], base: str) -> str:
    if not effects:
        return base
    head = effects[0]
    if head.type == "block":
        return f"lesson #{head.lesson_id}: {head.text}".strip()
    if head.type == "scale_size":
        return f"{base} · lesson #{head.lesson_id} ×{head.factor}"
    if head.type == "tighten_param":
        return f"{base} · lesson #{head.lesson_id} {head.param}"
    if head.type == "require_check":
        return f"{base} · lesson #{head.lesson_id} require {head.param or 'check'}"
    return f"{base} · lesson #{head.lesson_id}"
