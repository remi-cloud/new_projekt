"""Durable lessons and the in-process cache used before each decision."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.sqlite import db_session
from app.solana_desk.learning.dsl import matches, rule_key
from app.solana_desk.learning.guard import validate
from app.solana_desk.real_gate import redact

N_SHADOW = 5
MAX_ACTIVE = 25

_cache: dict[str, Any] = {"token": None, "rows": []}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


async def _token() -> str:
    async with db_session() as db:
        cur = await db.execute("SELECT COALESCE(MAX(id), 0) FROM solana_desk_lessons")
        row = await cur.fetchone()
    return str(row[0] if row else 0)


async def _load() -> list[dict]:
    token = await _token()
    if _cache["token"] == token:
        return list(_cache["rows"])
    async with db_session() as db:
        cur = await db.execute("SELECT * FROM solana_desk_lessons ORDER BY id ASC")
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    parsed = []
    for row in rows:
        item = dict(zip(cols, row))
        try:
            item["rule"] = json.loads(item.get("rule_json") or "{}")
        except json.JSONDecodeError:
            item["rule"] = {}
        parsed.append(item)
    _cache["token"] = token
    _cache["rows"] = parsed
    return list(parsed)


def invalidate() -> None:
    _cache["token"] = None


async def for_agent(agent: str, statuses: tuple[str, ...] = ("active", "shadow")) -> list[dict]:
    rows = await _load()
    return [row for row in rows if row.get("agent") == agent and row.get("status") in statuses]


async def count_by_status() -> dict[str, int]:
    rows = await _load()
    out = {"active": 0, "shadow": 0, "retired": 0, "rejected_unsafe": 0}
    for row in rows:
        status = str(row.get("status") or "")
        if status in out:
            out[status] += 1
    return out


async def latest_text(agent: str) -> str:
    rows = [row for row in await for_agent(agent, ("active",)) ]
    if not rows:
        return ""
    row = rows[-1]
    return str(row.get("lesson_text") or "")[:80]


async def save_lesson(
    *,
    agent: str,
    trigger: str,
    evidence: dict,
    diagnosis: str,
    lesson_text: str,
    rule: dict,
    source: str,
    confidence: float,
    settings: dict | None = None,
    model: str = "",
    trade_id: int | None = None,
    decision_id: int | None = None,
    deterministic: bool = False,
) -> dict:
    ok, why = validate(agent, rule, settings or {})
    key = rule_key(rule)
    status = "rejected_unsafe"
    if ok:
        status = _initial_status(source, confidence, deterministic)
        status = await _promote_repeat(agent, key, status)
    async with db_session() as db:
        cur = await db.execute(
            "SELECT id, created_at, status FROM solana_desk_lessons WHERE agent = ? AND rule_key = ? ORDER BY id DESC LIMIT 1",
            (agent, key),
        )
        existing = await cur.fetchone()
        if existing and ok:
            created = _parse_ts(existing[1])
            if created and datetime.now(timezone.utc) - created < timedelta(minutes=10):
                await db.execute(
                    "UPDATE solana_desk_lessons SET evidence_json = ?, confidence = ?, status = ? WHERE id = ?",
                    (redact(json.dumps(evidence, default=str))[:8000], confidence, status, existing[0]),
                )
                await db.commit()
                invalidate()
                return await get_lesson(int(existing[0]))
        cur = await db.execute(
            """
            INSERT INTO solana_desk_lessons (
                agent, trade_id, decision_id, trigger, evidence_json, diagnosis, lesson_text,
                rule_json, rule_key, source, model, confidence, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent,
                trade_id,
                decision_id,
                trigger,
                redact(json.dumps(evidence, default=str))[:8000],
                diagnosis[:500],
                lesson_text[:500],
                json.dumps(rule),
                key,
                source,
                model[:80],
                confidence,
                status,
                _now(),
            ),
        )
        lesson_id = int(cur.lastrowid)
        await db.commit()
    invalidate()
    await _cap(agent)
    return await get_lesson(lesson_id)


def _initial_status(source: str, confidence: float, deterministic: bool) -> str:
    if source == "llm" and not deterministic:
        return "shadow"
    if confidence < 0.7:
        return "shadow"
    return "active"


async def _promote_repeat(agent: str, key: str, status: str) -> str:
    async with db_session() as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM solana_desk_lessons WHERE agent = ? AND rule_key = ? AND status != 'rejected_unsafe'",
            (agent, key),
        )
        row = await cur.fetchone()
    if int(row[0] if row else 0) >= 1:
        return "active"
    return status


async def get_lesson(lesson_id: int) -> dict:
    async with db_session() as db:
        cur = await db.execute("SELECT * FROM solana_desk_lessons WHERE id = ?", (lesson_id,))
        row = await cur.fetchone()
        cols = [item[0] for item in cur.description]
    if not row:
        return {}
    item = dict(zip(cols, row))
    try:
        item["rule"] = json.loads(item.get("rule_json") or "{}")
    except json.JSONDecodeError:
        item["rule"] = {}
    return item


async def list_lessons(agent: str = "", status: str = "") -> list[dict]:
    clauses = ["1=1"]
    params: list[Any] = []
    if agent:
        clauses.append("agent = ?")
        params.append(agent)
    if status:
        clauses.append("status = ?")
        params.append(status)
    async with db_session() as db:
        cur = await db.execute(
            f"SELECT * FROM solana_desk_lessons WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT 200",
            params,
        )
        rows = await cur.fetchall()
        cols = [item[0] for item in cur.description]
    out = []
    for row in rows:
        item = dict(zip(cols, row))
        try:
            item["rule"] = json.loads(item.get("rule_json") or "{}")
        except json.JSONDecodeError:
            item["rule"] = {}
        if item.get("evidence_json"):
            item["evidence_json"] = redact(str(item["evidence_json"]))
        out.append(item)
    return out


async def set_status(lesson_id: int, status: str, reason: str = "") -> dict:
    row = await get_lesson(lesson_id)
    if not row:
        raise ValueError("lesson missing")
    if status == "active":
        ok, why = validate(str(row.get("agent")), row.get("rule") or {}, {})
        if not ok:
            raise ValueError(why or "guard rejected")
    retired_at = _now() if status == "retired" else None
    async with db_session() as db:
        await db.execute(
            "UPDATE solana_desk_lessons SET status = ?, retired_at = ?, retired_reason = ? WHERE id = ?",
            (status, retired_at, reason[:240], lesson_id),
        )
        await db.commit()
    invalidate()
    return await get_lesson(lesson_id)


async def record_hit(lesson_id: int, decision_id: int | None, effect: str, counterfactual: dict | None = None) -> None:
    applied = effect in {"blocked", "tightened", "scaled"}
    async with db_session() as db:
        await db.execute(
            """
            INSERT INTO solana_desk_lesson_hits (lesson_id, decision_id, ts, effect, counterfactual_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lesson_id, decision_id, _now(), effect, json.dumps(counterfactual or {})),
        )
        if applied and not (counterfactual or {}).get("shadow"):
            await db.execute(
                """
                UPDATE solana_desk_lessons
                SET times_applied = times_applied + 1,
                    times_blocked = times_blocked + ?,
                    last_applied_at = ?
                WHERE id = ?
                """,
                (1 if effect == "blocked" else 0, _now(), lesson_id),
            )
        await db.commit()
    invalidate()


async def shadow_matches(lesson_id: int) -> int:
    async with db_session() as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM solana_desk_lesson_hits WHERE lesson_id = ? AND effect = 'shadow'",
            (lesson_id,),
        )
        row = await cur.fetchone()
    return int(row[0] if row else 0)


async def maybe_promote_shadow(lesson_id: int) -> None:
    count = await shadow_matches(lesson_id)
    if count >= N_SHADOW:
        row = await get_lesson(lesson_id)
        if row.get("status") == "shadow":
            await set_status(lesson_id, "active", "shadow window complete")


async def _cap(agent: str) -> None:
    rows = await for_agent(agent, ("active",))
    if len(rows) <= MAX_ACTIVE:
        return
    ranked = sorted(rows, key=lambda item: (item.get("outcome_score") is None, item.get("outcome_score") or 0))
    extra = len(rows) - MAX_ACTIVE
    for row in ranked[:extra]:
        await set_status(int(row["id"]), "retired", "cap 25")


def public_lesson(row: dict) -> dict:
    """Guest view. Evidence is redacted again on the way out."""
    return {
        "id": row.get("id"),
        "agent": row.get("agent"),
        "trade_id": row.get("trade_id"),
        "decision_id": row.get("decision_id"),
        "trigger": row.get("trigger"),
        "diagnosis": row.get("diagnosis"),
        "lesson_text": row.get("lesson_text"),
        "rule": row.get("rule"),
        "source": row.get("source"),
        "model": row.get("model"),
        "confidence": row.get("confidence"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "last_applied_at": row.get("last_applied_at"),
        "times_applied": row.get("times_applied"),
        "times_blocked": row.get("times_blocked"),
        "outcome_trades": row.get("outcome_trades"),
        "outcome_pnl_sol": row.get("outcome_pnl_sol"),
        "outcome_score": row.get("outcome_score"),
        "retired_at": row.get("retired_at"),
        "retired_reason": row.get("retired_reason"),
        "evidence_redacted": True,
    }
