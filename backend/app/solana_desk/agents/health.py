"""Per-agent health. Status is derived from the stored timestamps."""

from __future__ import annotations

from datetime import datetime, timezone

from app.solana_desk.store import health_rows, record_health

AGENTS = ("scanner", "rug_check", "sizer", "executor", "logger", "equity")


def _age_seconds(stamp: str | None) -> float | None:
    if not stamp:
        return None
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moment).total_seconds()


async def beat(agent: str, *, ok: bool, latency_ms: int, error: str = "", checks: list | None = None, quote_ok: bool = False) -> None:
    await record_health(agent, ok=ok, latency_ms=latency_ms, error=error, checks=checks, quote_ok=quote_ok)


async def snapshot(interval_seconds: float = 10) -> dict[str, dict]:
    rows = await health_rows()
    out: dict[str, dict] = {}
    for agent in AGENTS:
        row = rows.get(agent) or {}
        out[agent] = {
            "status": _status(agent, row, interval_seconds),
            "last_run_at": row.get("last_run_at"),
            "latency_ms": row.get("last_latency_ms"),
            "error": row.get("last_error") or "",
            "checks": row.get("checks") or [],
            "runs": row.get("runs") or 0,
            "errors": row.get("errors") or 0,
        }
    return out


def _status(agent: str, row: dict, interval: float) -> str:
    if not row or not row.get("last_run_at"):
        return "idle"
    run_age = _age_seconds(row.get("last_run_at"))
    ok_age = _age_seconds(row.get("last_ok_at"))
    if agent == "scanner":
        if ok_age is None or ok_age > interval * 3:
            return "down"
        return "ok"
    if agent == "rug_check":
        checks = {item.get("name"): item for item in (row.get("checks") or []) if isinstance(item, dict)}
        rug_ok = (checks.get("rugcheck") or {}).get("ok")
        chain_ok = (checks.get("onchain") or {}).get("ok")
        if rug_ok is False and chain_ok is True:
            return "degraded"
        if rug_ok is False and chain_ok is False:
            return "down"
        if ok_age is None:
            return "down"
        return "ok"
    if agent == "executor":
        quote_age = _age_seconds(row.get("last_quote_ok_at"))
        if quote_age is None or quote_age > 60:
            if run_age is not None and run_age > 60:
                return "down"
            if quote_age is None and (row.get("errors") or 0) > 0:
                return "down"
        if (row.get("last_error") or "") and ok_age is None:
            return "down"
        return "ok" if row.get("last_ok_at") else "idle"
    if agent == "logger":
        if row.get("last_error") and (ok_age is None or (run_age is not None and ok_age is not None and ok_age > run_age)):
            return "down"
        return "ok" if row.get("last_ok_at") else "down"
    if agent == "equity":
        checks = {item.get("name"): item for item in (row.get("checks") or []) if isinstance(item, dict)}
        drift = checks.get("drift") or {}
        stale = checks.get("snapshot_age") or {}
        if drift.get("ok") is False or stale.get("ok") is False:
            return "degraded"
        return "ok" if row.get("last_ok_at") else "idle"
    if agent == "sizer":
        return "ok" if row.get("last_ok_at") else ("down" if row.get("last_error") else "idle")
    return "ok" if row.get("last_ok_at") else "idle"
