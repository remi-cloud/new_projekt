"""Global Session Clock — Asia/EU/US UTC sessions × meme heatmap × BTC/SOL log bias."""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# FX-style UTC windows (inclusive start, exclusive end for primary; overlaps allowed)
_SESSION_WINDOWS: dict[str, tuple[int, int]] = {
    "asia": (0, 8),
    "europe": (7, 16),
    "us": (13, 22),
    "overlap_eu_us": (13, 16),
}

_SESSION_LABELS = {
    "asia": "Asia (Tokyo/HK)",
    "europe": "Europe (London)",
    "us": "US (New York)",
    "overlap_eu_us": "EU∩US overlap",
    "off": "Off-hours",
}


def _enabled() -> bool:
    return bool(getattr(settings, "session_clock_enabled", True))


def _lookback_days() -> int:
    return max(3, min(30, int(getattr(settings, "session_clock_lookback_days", 14) or 14)))


def session_for_utc_hour(hour: int) -> str:
    """Primary session lane for a UTC hour (0–23). Prefer overlap when in 13–16."""
    h = int(hour) % 24
    if 13 <= h < 16:
        return "overlap_eu_us"
    if 0 <= h < 8:
        return "asia"
    if 7 <= h < 16:
        return "europe"
    if 13 <= h < 22:
        return "us"
    return "off"


def sessions_active_at_hour(hour: int) -> list[str]:
    h = int(hour) % 24
    out: list[str] = []
    for name, (start, end) in _SESSION_WINDOWS.items():
        if start <= h < end:
            out.append(name)
    if not out:
        out.append("off")
    return out


def log_return(prev: float, curr: float) -> float | None:
    if prev is None or curr is None or prev <= 0 or curr <= 0:
        return None
    try:
        return math.log(curr / prev)
    except (ValueError, ZeroDivisionError):
        return None


def build_meme_hour_heatmap(
    events: list[dict],
    *,
    candidates: list[dict] | None = None,
) -> dict[str, Any]:
    """Count buy/sell + USD and pair creates per UTC hour."""
    hours: dict[int, dict[str, float]] = {
        h: {"buys": 0, "sells": 0, "usd": 0.0, "creates": 0, "events": 0} for h in range(24)
    }
    for ev in events:
        ts = int(ev.get("ts_unix") or 0)
        if ts <= 0:
            continue
        h = datetime.fromtimestamp(ts, tz=timezone.utc).hour
        action = str(ev.get("action") or "").lower()
        usd = float(ev.get("usd_amount") or 0) or 0.0
        hours[h]["events"] += 1
        hours[h]["usd"] += usd
        if action == "buy":
            hours[h]["buys"] += 1
        elif action == "sell":
            hours[h]["sells"] += 1
    for c in candidates or []:
        ms = c.get("pair_created_ms")
        if not ms:
            continue
        try:
            ms_i = int(ms)
        except (TypeError, ValueError):
            continue
        ts = ms_i // 1000 if ms_i > 10_000_000_000 else ms_i
        if ts <= 0:
            continue
        h = datetime.fromtimestamp(ts, tz=timezone.utc).hour
        hours[h]["creates"] += 1

    rows = []
    for h in range(24):
        cell = hours[h]
        activity = cell["buys"] + cell["sells"] + cell["creates"] + cell["events"] * 0.25
        rows.append(
            {
                "hour_utc": h,
                "session": session_for_utc_hour(h),
                "buys": int(cell["buys"]),
                "sells": int(cell["sells"]),
                "creates": int(cell["creates"]),
                "usd": round(cell["usd"], 2),
                "activity": round(activity, 2),
            }
        )
    hot = sorted(rows, key=lambda r: -float(r["activity"]))[:3]
    by_session: dict[str, float] = defaultdict(float)
    for r in rows:
        by_session[str(r["session"])] += float(r["activity"])
    return {
        "hours": rows,
        "hot_hours": hot,
        "session_activity": {k: round(v, 2) for k, v in by_session.items()},
        "hottest_session": max(by_session, key=by_session.get) if by_session else "off",
    }


async def build_macro_session_bias(*, lookback_days: int | None = None) -> dict[str, Any]:
    """Hourly log-return bias for BTC + SOL over recent bars."""
    from app.data.chart_data import fetch_chart

    days = lookback_days if lookback_days is not None else _lookback_days()
    symbols = ["BTC-USD", "SOL-USD"]
    hour_logs: dict[int, list[float]] = defaultdict(list)
    session_logs: dict[str, list[float]] = defaultdict(list)
    used_bars = 0

    for sym in symbols:
        try:
            chart = await fetch_chart(sym, "1H")
        except Exception as exc:
            logger.debug("session clock chart %s: %s", sym, exc)
            continue
        if not chart or not chart.candles:
            continue
        candles = list(chart.candles)
        # Keep roughly lookback_days of hours
        max_bars = max(24, days * 24)
        candles = candles[-max_bars:]
        for i in range(1, len(candles)):
            prev_c = candles[i - 1].close
            curr = candles[i]
            lr = log_return(float(prev_c), float(curr.close))
            if lr is None:
                continue
            ts = int(curr.time)
            h = datetime.fromtimestamp(ts, tz=timezone.utc).hour
            hour_logs[h].append(lr)
            for sess in sessions_active_at_hour(h):
                if sess == "off":
                    continue
                session_logs[sess].append(lr)
            used_bars += 1

    hours_out = []
    for h in range(24):
        vals = hour_logs.get(h) or []
        avg = sum(vals) / len(vals) if vals else 0.0
        hours_out.append(
            {
                "hour_utc": h,
                "session": session_for_utc_hour(h),
                "avg_log_return": round(avg, 6),
                "n": len(vals),
            }
        )

    sessions_out = []
    for name in ("asia", "europe", "us", "overlap_eu_us"):
        vals = session_logs.get(name) or []
        avg = sum(vals) / len(vals) if vals else 0.0
        bias = "bull" if avg > 0.0005 else ("bear" if avg < -0.0005 else "neutral")
        sessions_out.append(
            {
                "session": name,
                "label": _SESSION_LABELS.get(name, name),
                "avg_log_return": round(avg, 6),
                "n": len(vals),
                "bias": bias,
            }
        )
    sessions_out.sort(key=lambda s: -float(s["avg_log_return"]))
    return {
        "symbols": symbols,
        "lookback_days": days,
        "bars_used": used_bars,
        "hours": hours_out,
        "sessions": sessions_out,
        "strongest_session": sessions_out[0]["session"] if sessions_out else None,
    }


def month_overlay_from_global_book() -> dict[str, Any]:
    """Soft month weights from global cycle book profiles (asia/eu/us/crypto)."""
    try:
        from app.cycles.global_cycle_book import get_global_cycle_book

        book = get_global_cycle_book(status="all")
    except Exception as exc:
        logger.debug("global book overlay: %s", exc)
        return {"month": datetime.now(timezone.utc).month, "regions": {}}

    month = datetime.now(timezone.utc).month
    profiles = book.get("profiles") or {}
    regions: dict[str, Any] = {}
    mapping = {"asia": "asia", "eu": "europe", "europe": "europe", "us": "us", "crypto": "crypto"}
    for uid, p in profiles.items():
        key = mapping.get(str(uid).lower())
        if not key:
            continue
        months = p.get("months") or []
        cell = next((m for m in months if int(m.get("month") or 0) == month), None)
        if not cell:
            continue
        regions[key] = {
            "avg_return_pct": cell.get("avg_return_pct"),
            "bias": cell.get("bias"),
            "n": cell.get("n"),
            "label": p.get("label") or uid,
        }
    return {"month": month, "regions": regions}


def session_boost_for_timestamp(
    ts_unix: int | None,
    *,
    hottest_session: str | None = None,
    macro_strongest: str | None = None,
) -> tuple[float, list[str]]:
    """Soft +0…+12 boost + tags when create/event aligns with hot sessions."""
    if not ts_unix or ts_unix <= 0:
        return 0.0, []
    h = datetime.fromtimestamp(int(ts_unix), tz=timezone.utc).hour
    sess = session_for_utc_hour(h)
    tags: list[str] = []
    if sess == "asia" or (sess == "off" and 0 <= h < 8):
        tags.append("session_asia")
    if sess in ("europe", "overlap_eu_us") or 7 <= h < 16:
        if "session_eu" not in tags:
            tags.append("session_eu")
    if sess in ("us", "overlap_eu_us") or 13 <= h < 22:
        if "session_us" not in tags:
            tags.append("session_us")
    if sess == "overlap_eu_us":
        tags.append("session_overlap")

    boost = 0.0
    if hottest_session and sess == hottest_session:
        boost += 8.0
    elif hottest_session and sess != "off" and hottest_session in sessions_active_at_hour(h):
        boost += 5.0
    if macro_strongest and (sess == macro_strongest or macro_strongest in sessions_active_at_hour(h)):
        boost += 4.0
    return min(12.0, boost), tags


async def run_session_clock(
    *,
    events: list[dict] | None = None,
    candidates: list[dict] | None = None,
) -> dict[str, Any]:
    """Build full snapshot and persist to launch_state."""
    if not _enabled():
        return {"ok": False, "reason": "disabled", "brand": "Session Clock"}

    if events is None or candidates is None:
        try:
            from app.launch_scout import db as launch_db

            await launch_db.init_launch_scout_db()
            if events is None:
                events = await launch_db.list_trader_events(limit=500)
            if candidates is None:
                candidates = await launch_db.list_candidates(tier=None, limit=200)
        except Exception as exc:
            logger.warning("session clock load launch data: %s", exc)
            events = events or []
            candidates = candidates or []

    now = datetime.now(timezone.utc)
    hour = now.hour
    heatmap = build_meme_hour_heatmap(events or [], candidates=candidates or [])
    try:
        macro = await build_macro_session_bias()
    except Exception as exc:
        logger.warning("session clock macro bias: %s", exc)
        macro = {"sessions": [], "hours": [], "strongest_session": None, "error": str(exc)[:160]}
    month = month_overlay_from_global_book()

    now_session = session_for_utc_hour(hour)
    active = sessions_active_at_hour(hour)
    result: dict[str, Any] = {
        "ok": True,
        "enabled": True,
        "brand": "Session Clock",
        "priority": "P2",
        "at": now.isoformat(),
        "now_hour_utc": hour,
        "now_session": now_session,
        "now_session_label": _SESSION_LABELS.get(now_session, now_session),
        "active_lanes": active,
        "heatmap": heatmap,
        "macro_bias": macro,
        "month_overlay": month,
        "hot_lane": heatmap.get("hottest_session"),
        "note": (
            "UTC session map (Asia→EU→US) + meme event heatmap + BTC/SOL hourly log-returns. "
            "Educational timetable — not a prediction of a specific tick."
        ),
    }
    try:
        from app.launch_scout import db as launch_db

        await launch_db.init_launch_scout_db()
        await launch_db.set_state("session_clock_json", json.dumps(result, ensure_ascii=False)[:120_000])
    except Exception as exc:
        logger.debug("session_clock_json persist: %s", exc)
    return result


async def get_session_clock_snapshot() -> dict[str, Any]:
    if not _enabled():
        return {"ok": False, "reason": "disabled", "brand": "Session Clock", "priority": "P2"}
    try:
        from app.launch_scout import db as launch_db

        await launch_db.init_launch_scout_db()
        raw = await launch_db.get_state("session_clock_json")
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("heatmap") is not None:
                data["ok"] = True
                data["enabled"] = True
                # Refresh "now" fields without full rebuild
                now = datetime.now(timezone.utc)
                data["now_hour_utc"] = now.hour
                data["now_session"] = session_for_utc_hour(now.hour)
                data["now_session_label"] = _SESSION_LABELS.get(data["now_session"], data["now_session"])
                data["active_lanes"] = sessions_active_at_hour(now.hour)
                return data
    except Exception:
        pass
    return await run_session_clock()
