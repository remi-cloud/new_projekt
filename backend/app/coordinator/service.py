"""Coordinator — aggregate agent health (P0–P3) without blocking desk ticks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.coordinator.link_guard import audit_terminal_urls

logger = logging.getLogger(__name__)

_last_health: dict[str, Any] | None = None
_last_tick_at: str | None = None
_app_started_at: datetime | None = None


def mark_app_started() -> None:
    global _app_started_at
    _app_started_at = datetime.now(timezone.utc)


def _in_startup_grace(max_interval_sec: int) -> bool:
    if _app_started_at is None:
        return False
    age = (datetime.now(timezone.utc) - _app_started_at).total_seconds()
    return age < max(60, max_interval_sec * 2)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        raw = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _stale(last_tick: str | None, interval_sec: int) -> bool:
    dt = _parse_iso(last_tick)
    if dt is None:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return age > max(60, interval_sec * 3)


def _desk_ok(
    *,
    last_tick: str | None,
    interval_sec: int,
    last_error: str | None,
    in_grace: bool,
) -> bool:
    if last_error:
        return False
    if not _stale(last_tick, interval_sec):
        return True
    return in_grace and not last_tick


async def _desk_status() -> dict[str, Any]:
    from app.axiom.service import get_axiom_status
    from app.fomo.service import get_fomo_status
    from app.launch_scout.service import get_launch_status, list_launch_candidates

    launch = await get_launch_status()
    axiom = await get_axiom_status()
    fomo = await get_fomo_status()

    launch_iv = int(launch.get("interval_seconds") or 60)
    axiom_iv = int(axiom.get("interval_seconds") or 90)
    fomo_iv = int(getattr(settings, "fomo_interval_seconds", 60) or 60)
    in_grace = _in_startup_grace(max(launch_iv, axiom_iv, fomo_iv))

    sample = await list_launch_candidates(tier="all", limit=50)
    link_guard = audit_terminal_urls(sample)

    def _pack(
        raw: dict[str, Any],
        interval_sec: int,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_tick = raw.get("last_tick_at")
        last_error = raw.get("last_error")
        warming = in_grace and not last_tick and not last_error
        row: dict[str, Any] = {
            "ok": _desk_ok(
                last_tick=last_tick,
                interval_sec=interval_sec,
                last_error=last_error,
                in_grace=in_grace,
            ),
            "last_tick_at": last_tick,
            "last_error": last_error,
            "interval_seconds": interval_sec,
            "warming_up": warming,
        }
        if extra:
            row.update(extra)
        return row

    return {
        "launch": _pack(
            launch,
            launch_iv,
            extra={"counts": launch.get("counts"), "link_guard": link_guard},
        ),
        "axiom": _pack(
            axiom,
            axiom_iv,
            extra={
                "pulse_count": axiom.get("pulse_count"),
                "positions_open": axiom.get("positions_open"),
            },
        ),
        "fomo": _pack(
            fomo,
            fomo_iv,
            extra={"traders_count": fomo.get("traders_count")},
        ),
        "_in_grace": in_grace,
    }


async def get_coordinator_health() -> dict[str, Any]:
    global _last_health
    if _last_health:
        return _last_health
    return await run_coordinator_tick()


async def run_coordinator_tick() -> dict[str, Any]:
    global _last_health, _last_tick_at

    now_iso = datetime.now(timezone.utc).isoformat()
    desks_raw = await _desk_status()
    in_grace = bool(desks_raw.pop("_in_grace", False))
    desks = desks_raw
    warnings: list[str] = []
    desks_stale: list[str] = []
    hard_errors: list[str] = []

    for name, st in desks.items():
        if st.get("last_error"):
            msg = f"{name}: error ({st.get('last_error')})"
            hard_errors.append(msg)
            warnings.append(msg)
            logger.warning("Coordinator: %s", msg)
        elif not st.get("ok"):
            msg = f"{name}: stale ({st.get('last_tick_at') or 'no tick'})"
            desks_stale.append(msg)
            warnings.append(msg)
            logger.warning("Coordinator: %s", msg)

    lg = desks.get("launch", {}).get("link_guard") or {}
    if not lg.get("ok"):
        warnings.append(
            f"link_guard: bad_4meme={lg.get('bad_4meme')} missing_chain_axiom={lg.get('missing_chain_axiom')}"
        )

    binance_bridge: dict[str, Any] = {"ok": True, "mode": "offline"}
    binance_bot: dict[str, Any] = {}
    try:
        from app.integrations.binance_ai_bridge import get_binance_ai_context

        binance_bridge = await get_binance_ai_context()
        binance_bridge["ok"] = True
    except Exception as exc:
        binance_bridge = {"ok": False, "error": str(exc)[:200]}

    try:
        from app.integrations.binance_ai_agent import get_binance_bot_status
        from app.integrations.portfolio_binance_bridge import build_binance_sync

        sync = await build_binance_sync()
        bot = get_binance_bot_status()
        binance_bot = {
            "ok": True,
            "enabled": bot.get("enabled"),
            "dry_run": bot.get("dry_run"),
            "last_tick_at": bot.get("last_tick_at"),
            "connected": sync.get("connected"),
            "drift_count": sync.get("drift_count"),
        }
    except Exception as exc:
        binance_bot = {"ok": False, "error": str(exc)[:200]}

    link_guard_ok = lg.get("ok", True)
    health = {
        "ok": len(hard_errors) == 0 and link_guard_ok and (len(desks_stale) == 0 or in_grace),
        "at": now_iso,
        "startup_grace": in_grace,
        "priorities": {
            "P0": ["link_guard", "tick_watchdog"],
            "P1": ["launch_scout", "axiom", "fomo_ghost"],
            "P2": ["singularity", "finance_agent", "execution_agent", "binance_ai_bot"],
            "P3": ["newsletter", "business_leads", "alerts"],
        },
        "desks": desks,
        "binance_bridge": {
            "ok": binance_bridge.get("ok", True),
            "mode": binance_bridge.get("mode"),
            "source": binance_bridge.get("source"),
        },
        "binance_bot": binance_bot,
        "desks_stale": desks_stale,
        "hard_errors": hard_errors,
        "warnings": warnings,
    }

    _last_health = health
    _last_tick_at = now_iso
    return health
