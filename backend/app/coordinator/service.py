"""Coordinator — aggregate agent health (P0–P3) without blocking desk ticks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.coordinator.link_guard import audit_axiom_urls, audit_terminal_urls, link_guard_bad_count, link_guard_ok

logger = logging.getLogger(__name__)

_last_health: dict[str, Any] | None = None
_last_tick_at: str | None = None
_app_started_at: datetime | None = None
_CACHE_MAX_AGE_SEC = 90


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
    degraded: bool = False,
) -> bool:
    if last_error and not degraded:
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
    try:
        from app.axiom.service import list_axiom_positions, list_axiom_pulse

        pulse_sample = await list_axiom_pulse(limit=40)
        pos_sample = await list_axiom_positions(limit=40, status=None)
        axiom_links = audit_axiom_urls(pulse_sample, pos_sample)
        if not axiom_links.get("ok"):
            link_guard = {
                **link_guard,
                "axiom_checked": axiom_links.get("checked"),
                "axiom_missing_chain": axiom_links.get("missing_chain_axiom"),
                "axiom_bad_4meme": axiom_links.get("bad_4meme"),
                "ok": link_guard_ok({**link_guard, "axiom_missing_chain": axiom_links.get("missing_chain_axiom"), "axiom_bad_4meme": axiom_links.get("bad_4meme")}),
            }
        else:
            link_guard = {**link_guard, "axiom_checked": axiom_links.get("checked"), "axiom_ok": True}
    except Exception:
        pass

    launch_warnings = launch.get("last_warnings")

    def _pack(
        raw: dict[str, Any],
        interval_sec: int,
        *,
        extra: dict[str, Any] | None = None,
        degraded: bool = False,
        degraded_reason: str | None = None,
    ) -> dict[str, Any]:
        last_tick = raw.get("last_tick_at")
        last_error = raw.get("last_error")
        warming = in_grace and not last_tick and not last_error and not degraded
        row: dict[str, Any] = {
            "ok": _desk_ok(
                last_tick=last_tick,
                interval_sec=interval_sec,
                last_error=last_error,
                in_grace=in_grace,
                degraded=degraded,
            ),
            "last_tick_at": last_tick,
            "last_error": last_error,
            "interval_seconds": interval_sec,
            "warming_up": warming,
        }
        if degraded:
            row["degraded"] = True
            row["degraded_reason"] = degraded_reason
        if extra:
            row.update(extra)
        return row

    fomo_degraded = str(fomo.get("mode") or "") == "degraded"
    fomo_reason = str(fomo.get("degraded_reason") or fomo.get("source") or "")

    return {
        "launch": _pack(
            launch,
            launch_iv,
            extra={"counts": launch.get("counts"), "link_guard": link_guard, "last_warnings": launch_warnings},
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
            degraded=fomo_degraded,
            degraded_reason=fomo_reason if fomo_degraded else None,
        ),
        "_in_grace": in_grace,
    }


async def get_coordinator_health() -> dict[str, Any]:
    global _last_health, _last_tick_at
    if _last_health and _last_tick_at:
        dt = _parse_iso(_last_tick_at)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            if age < _CACHE_MAX_AGE_SEC:
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
        if st.get("degraded"):
            msg = f"{name}: degraded ({st.get('degraded_reason') or 'upstream offline'})"
            warnings.append(msg)
            if st.get("last_warnings"):
                warnings.append(f"{name}: {st.get('last_warnings')}")
            continue
        if st.get("last_warnings"):
            warnings.append(f"{name}: {st.get('last_warnings')}")
        if st.get("last_error"):
            msg = f"{name}: error ({st.get('last_error')})"
            warnings.append(msg)
            logger.warning("Coordinator desk warning: %s", msg)
        elif not st.get("ok"):
            msg = f"{name}: stale ({st.get('last_tick_at') or 'no tick'})"
            desks_stale.append(msg)
            warnings.append(msg)
            logger.warning("Coordinator: %s", msg)

    lg = desks.get("launch", {}).get("link_guard") or {}
    if not link_guard_ok(lg):
        hard_errors.append(
            f"link_guard: bad={link_guard_bad_count(lg)} "
            f"(4meme={lg.get('bad_4meme')} launch_chain={lg.get('missing_chain_axiom')} "
            f"axiom_chain={lg.get('axiom_missing_chain')})"
        )
        warnings.append(hard_errors[-1])

    wallet_scout: dict[str, Any] = {"ok": True, "priority": "P0"}
    try:
        from app.launch_scout.wallet_scout import get_wallet_scout_snapshot

        ws = await get_wallet_scout_snapshot(limit=5)
        wallet_scout = {
            "ok": True,
            "priority": "P0",
            "open_bags": ws.get("open_bags"),
            "wallets_scanned": ws.get("wallets_scanned"),
            "top_n": ws.get("top_n"),
        }
    except Exception as exc:
        wallet_scout = {"ok": False, "priority": "P0", "error": str(exc)[:200]}
        hard_errors.append(f"wallet_scout: {exc}")
        warnings.append(f"wallet_scout: {exc}")

    dex_arena: dict[str, Any] = {"ok": True, "priority": "P1"}
    try:
        from app.launch_scout.dex_arena import get_dex_arena_snapshot

        arena = await get_dex_arena_snapshot()
        dex_arena = {
            "ok": bool(arena.get("ok", True)) and arena.get("reason") != "disabled",
            "priority": "P1",
            "boards": len(arena.get("boards") or []),
            "whale_mints_tracked": arena.get("whale_mints_tracked"),
            "enabled": arena.get("enabled", True),
        }
        if arena.get("reason") == "disabled":
            dex_arena["ok"] = True  # disabled is not a hard fail
    except Exception as exc:
        dex_arena = {"ok": False, "priority": "P1", "error": str(exc)[:200]}
        warnings.append(f"dex_arena: {exc}")

    session_clock: dict[str, Any] = {"ok": True, "priority": "P2"}
    try:
        from app.cycles.session_clock import get_session_clock_snapshot

        clock = await get_session_clock_snapshot()
        session_clock = {
            "ok": bool(clock.get("ok", True)) or clock.get("reason") == "disabled",
            "priority": "P2",
            "now_session": clock.get("now_session"),
            "hot_lane": clock.get("hot_lane"),
            "enabled": clock.get("enabled", True),
        }
    except Exception as exc:
        session_clock = {"ok": False, "priority": "P2", "error": str(exc)[:200]}
        warnings.append(f"session_clock: {exc}")

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

    wallet_scout_ok = bool(wallet_scout.get("ok", True))
    health = {
        "ok": len(hard_errors) == 0
        and wallet_scout_ok
        and (len(desks_stale) == 0 or in_grace),
        "at": now_iso,
        "startup_grace": in_grace,
        "priorities": {
            "P0": ["link_guard", "wallet_scout", "tick_watchdog"],
            "P1": ["launch_scout", "dex_arena", "axiom", "fomo_ghost"],
            "P2": ["singularity", "finance_agent", "execution_agent", "binance_ai_bot", "session_clock"],
            "P3": ["newsletter", "business_leads", "alerts"],
        },
        "wallet_scout": wallet_scout,
        "dex_arena": dex_arena,
        "session_clock": session_clock,
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
