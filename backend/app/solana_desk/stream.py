"""SSE for the terminal. The API polls SQLite because the worker may be another process."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable

from app.solana_desk.store import decisions_after, latest_decision_id
from app.solana_desk.terminal import build_terminal, decision_public


async def iter_events(
    last_event_id: int = 0,
    *,
    sleep: Callable[[float], Awaitable[None]],
    max_cycles: int | None = None,
    heartbeat_every: int = 15,
) -> AsyncIterator[str]:
    last_id = int(last_event_id or 0)
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        snapshot = await build_terminal()
        yield _frame("snapshot", snapshot, event_id=await latest_decision_id())
        fresh = await decisions_after(last_id, limit=50)
        for row in fresh:
            last_id = int(row["id"])
            kind = "lesson" if str(row.get("kind") or "") == "LESSON" else "decision"
            yield _frame(kind, decision_public(row), event_id=last_id)
        if cycles and cycles % heartbeat_every == 0:
            yield _frame("heartbeat", {"ok": True}, event_id=last_id)
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            break
        await sleep(1)


def _frame(event: str, payload: dict, event_id: int) -> str:
    body = json.dumps(payload, ensure_ascii=False, default=str)
    return f"id: {event_id}\nevent: {event}\ndata: {body}\n\n"
