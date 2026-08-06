"""Pearl hunter service façade."""

from __future__ import annotations

from app.ai.pearl_hunter import db as pearl_db
from app.ai.pearl_hunter.crypto_agent import AGENT_ID as CRYPTO_ID
from app.ai.pearl_hunter.crypto_agent import run_crypto_agent
from app.ai.pearl_hunter.equity_agent import AGENT_ID as EQUITY_ID
from app.ai.pearl_hunter.equity_agent import run_equity_agent
from app.config import settings


async def list_pearl_finds(limit: int = 40, agent_id: str | None = None) -> list[dict]:
    return await pearl_db.list_finds(limit=limit, agent_id=agent_id)


async def get_pearl_status() -> dict:
    runs = await pearl_db.get_runs()
    by_id = {r["agent_id"]: r for r in runs}
    agents = []
    for agent_id, label in (
        (EQUITY_ID, "Equity Pearl Hunter"),
        (CRYPTO_ID, "Crypto Pearl Hunter"),
    ):
        r = by_id.get(agent_id) or {}
        agents.append(
            {
                "id": agent_id,
                "name": label,
                "last_run_at": r.get("last_run_at"),
                "last_count": r.get("last_count") or 0,
                "last_error": r.get("last_error") or "",
            }
        )
    last_times = [a["last_run_at"] for a in agents if a.get("last_run_at")]
    last_run = max(last_times) if last_times else None
    return {
        "enabled": bool(getattr(settings, "pearl_hunter_enabled", True)),
        "agents": agents,
        "finds_count": await pearl_db.count_finds(),
        "last_run_at": last_run,
    }


__all__ = [
    "get_pearl_status",
    "list_pearl_finds",
    "run_crypto_agent",
    "run_equity_agent",
]
