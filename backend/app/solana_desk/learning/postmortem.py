"""Queued post-mortem. The LLM proposes a rule; a miner fills in when it cannot."""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Awaitable, Callable

from app.solana_desk.learning.dsl import parse_proposal
from app.solana_desk.learning.memory import save_lesson
from app.solana_desk.store import read_state, write_state

log = logging.getLogger("app.solana_desk.learning")

_SYSTEM = """You are the post-mortem for one Solana desk agent.
Return JSON only, no markdown:
{"agent":"...","diagnosis":"...","lesson_text":"...","rule":{"when":[{"feature":"...","op":">=","value":0}],"action":{"type":"block","param":null,"value":null,"factor":null}},"confidence":0.0}
Rules may only get stricter. Never raise a size, slippage, or loss limit. Never mention keys or RPC.
"""


async def review(
    evidence: dict,
    *,
    settings: dict | None = None,
    complete: Callable[..., Awaitable[str]] | None = None,
) -> dict | None:
    """One LLM attempt (plus a single retry). Invalid output falls back to the miner."""
    agent = str(evidence.get("agent") or "")
    if not agent:
        return None
    trade_id = evidence.get("trade_id")
    source = "rule"
    model = ""
    proposal = None
    if complete is not None or await _llm_allowed(trade_id):
        proposal, model = await _ask(evidence, complete)
        if proposal is not None:
            source = "llm"
            if trade_id is not None:
                await write_state(f"pm_llm_{trade_id}", "1")
    mined = mine_rule(agent, evidence)
    deterministic = False
    if proposal is not None and mined is not None:
        deterministic = proposal.rule.model_dump() == mined or _same_action(proposal.rule.model_dump(), mined)
    if proposal is None:
        if mined is None:
            return None
        rule = mined
        text = _text(agent, rule)
        diagnosis = "rule miner"
        confidence = 0.8
        source = "rule"
    else:
        rule = proposal.rule.model_dump()
        text = proposal.lesson_text
        diagnosis = proposal.diagnosis
        confidence = float(proposal.confidence)
        if mined is not None and not deterministic and confidence < 0.7:
            rule = mined
            source = "rule"
            confidence = 0.8
            text = _text(agent, rule)
    return await save_lesson(
        agent=agent,
        trigger=str(evidence.get("trigger") or "close"),
        evidence=evidence,
        diagnosis=diagnosis,
        lesson_text=text,
        rule=rule,
        source=source,
        confidence=confidence,
        settings=settings,
        model=model,
        trade_id=trade_id if isinstance(trade_id, int) else None,
        decision_id=evidence.get("decision_id") if isinstance(evidence.get("decision_id"), int) else None,
        deterministic=deterministic or source == "rule",
    )


async def _llm_allowed(trade_id: object) -> bool:
    if trade_id is None:
        return True
    return (await read_state(f"pm_llm_{trade_id}")) is None


async def _ask(evidence: dict, complete: Callable[..., Awaitable[str]] | None):
    caller = complete
    model = "provider"
    if caller is None:
        try:
            from app.ai.llm import llm_configured, simple_complete

            if not llm_configured():
                return None, ""
            caller = simple_complete
        except Exception:
            return None, ""
    user = json.dumps(evidence, default=str)[:6000]
    last = ""
    for _ in range(2):
        try:
            last = await caller(_SYSTEM, user, 0.2)
            return parse_proposal(last), model
        except Exception as exc:
            log.info("Post-mortem output dropped: %s", exc.__class__.__name__)
            last = ""
    return None, ""


def mine_rule(agent: str, evidence: dict) -> dict | None:
    features = evidence.get("features") or {}
    trigger = str(evidence.get("trigger") or "")
    dev = _num(features.get("dev_pct"))
    if agent == "rug_check" and dev is not None and dev >= 8 and trigger in {"rug_gap", "loss", "sell_fail", "close"}:
        floor = math.floor(dev)
        return _block([("dev_pct", ">=", float(floor))])
    liq = _num(features.get("liquidity_usd"))
    if agent == "sizer" and trigger in {"slippage", "oversize", "loss"} and liq is not None and liq < 10000:
        return {
            "when": [{"feature": "liquidity_usd", "op": "<", "value": 10000}],
            "action": {"type": "scale_size", "param": None, "value": None, "factor": 0.8},
        }
    spike = _num(features.get("spike"))
    fade = _num(features.get("fade_pct"))
    if agent == "scanner" and spike is not None and spike >= 3 and (fade or 0) > 5:
        return _block([("spike", ">=", 3.0), ("fade_pct", ">", 5.0)])
    if agent == "executor" and trigger in {"confirm_fail", "retry", "slippage"}:
        fee = _num(features.get("priority_fee_sol")) or 0.00005
        raised = min(0.01, max(fee * 4, 0.0002))
        return {
            "when": [{"feature": "priority_fee_sol", "op": "<=", "value": fee}],
            "action": {"type": "tighten_param", "param": "priority_fee_sol", "value": raised},
        }
    if agent == "equity" and trigger in {"drift", "stale", "mark_gap"}:
        return {
            "when": [{"feature": "drift_pct", "op": ">=", "value": 0.5}],
            "action": {"type": "require_check", "param": "reconcile", "value": None, "factor": None},
        }
    if agent == "logger" and trigger in {"empty_reason", "line_gap"}:
        return {
            "when": [],
            "action": {"type": "require_check", "param": "reason_source", "value": None, "factor": None},
        }
    if agent == "llm" and trigger in {"correction", "critic", "tool_error"}:
        return {
            "when": [],
            "action": {"type": "require_check", "param": "prompt", "value": None, "factor": None},
        }
    return None


def _block(conds: list[tuple[str, str, float]]) -> dict:
    return {
        "when": [{"feature": name, "op": op, "value": value} for name, op, value in conds],
        "action": {"type": "block", "param": None, "value": None, "factor": None},
    }


def _text(agent: str, rule: dict) -> str:
    action = rule.get("action") or {}
    if action.get("type") == "block":
        bits = [f"{item['feature']} {item['op']} {item['value']}" for item in rule.get("when") or []]
        return f"{agent} block when " + ", ".join(bits)
    if action.get("type") == "scale_size":
        return f"size ×{action.get('factor')} when liquidity is thin"
    if action.get("type") == "tighten_param":
        return f"{action.get('param')} → {action.get('value')}"
    return f"{agent} {action.get('type')} {action.get('param') or ''}".strip()


def _same_action(left: dict, right: dict) -> bool:
    return (left.get("action") or {}).get("type") == (right.get("action") or {}).get("type")


def _num(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


_PENDING: list[dict] = []


def queue(evidence: dict) -> None:
    """Park a post-mortem. The tick drains the queue after the candidate is logged."""
    _PENDING.append(evidence)


async def drain() -> int:
    done = 0
    while _PENDING:
        evidence = _PENDING.pop(0)
        try:
            await review(evidence)
            done += 1
        except Exception:
            log.exception("post-mortem failed")
    return done


async def score_blocks(desk_win_rate: float) -> list[int]:
    """Retire block lessons whose blocked names would have beaten the desk."""
    from app.solana_desk.learning.memory import for_agent, get_lesson, set_status
    from app.solana_desk.store import ticks_for

    retired: list[int] = []
    for agent in ("scanner", "rug_check", "sizer", "executor", "logger", "equity"):
        for row in await for_agent(agent, ("active",)):
            action = (row.get("rule") or {}).get("action") or {}
            if action.get("type") != "block":
                continue
            hits = await _hits(int(row["id"]))
            if len(hits) < 10:
                continue
            wins = 0
            pnl = 0.0
            for hit in hits:
                facts = hit.get("facts") or {}
                price = _num(facts.get("price"))
                mint = str(facts.get("mint") or "")
                ts = str(facts.get("ts") or "")
                if not mint or not price:
                    continue
                later = await ticks_for(mint, since_iso=ts, limit=50)
                if not later:
                    continue
                future = float(later[-1]["price"])
                change = (future - price) / price
                if change >= 0.25:
                    wins += 1
                    pnl += change
                elif change <= -0.06:
                    pnl += -0.06
                else:
                    pnl += change
                    if change > 0:
                        wins += 1
            rate = wins / len(hits)
            if pnl > 0 and rate > desk_win_rate + 0.10:
                await set_status(int(row["id"]), "retired", "counterfactual beat the desk")
                retired.append(int(row["id"]))
                continue
            if len(hits) >= 10 and await _block_share(agent) > 0.60:
                await set_status(int(row["id"]), "retired", "blocked more than 60% of candidates")
                retired.append(int(row["id"]))
    return retired


async def _hits(lesson_id: int) -> list[dict]:
    from app.db.sqlite import db_session

    async with db_session() as db:
        cur = await db.execute(
            "SELECT counterfactual_json FROM solana_desk_lesson_hits WHERE lesson_id = ? AND effect = 'blocked'",
            (lesson_id,),
        )
        rows = await cur.fetchall()
    out = []
    for (raw,) in rows:
        try:
            out.append({"facts": json.loads(raw or "{}").get("features") or json.loads(raw or "{}")})
        except json.JSONDecodeError:
            continue
    return out


async def _block_share(agent: str) -> float:
    from app.db.sqlite import db_session

    async with db_session() as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM solana_desk_decisions WHERE agent = ? AND kind IN ('SCAN', 'FILTER', 'SKIP', 'PASS')",
            (agent,),
        )
        total = int((await cur.fetchone())[0] or 0)
        cur = await db.execute(
            "SELECT COUNT(*) FROM solana_desk_decisions WHERE agent = ? AND reason LIKE 'lesson #%'",
            (agent,),
        )
        blocked = int((await cur.fetchone())[0] or 0)
    if total <= 0:
        return 0.0
    return blocked / total
