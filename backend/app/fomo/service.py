"""FOMO Ghost service — top-30 leaderboard + bag-in activity via Cope Capital."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.fomo import db as fomo_db
from app.fomo.client import CopeClient, normalize_activity, normalize_trader, resolve_cope_api_key
from app.fomo.offline import humanize_cope_error, is_cope_unreachable, seed_bag_events, seed_traders
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)

_KEY_FILE = Path(__file__).resolve().parents[2] / "data" / "cope_api_key.txt"


def _fomo_enabled() -> bool:
    return bool(getattr(settings, "fomo_enabled", True))


def _top_n() -> int:
    return max(1, min(50, int(getattr(settings, "fomo_top_n", 30) or 30)))


def _timeframe() -> str:
    tf = str(getattr(settings, "fomo_leaderboard_timeframe", "7d") or "7d")
    return tf if tf in ("24h", "7d", "30d", "all") else "7d"


def load_persisted_key() -> str:
    try:
        if _KEY_FILE.is_file():
            return _KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def persist_api_key(key: str) -> None:
    key = key.strip()
    if not key:
        return
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_text(key + "\n", encoding="utf-8")
    try:
        _KEY_FILE.chmod(0o600)
    except OSError:
        pass
    _sync_key_to_dotenv(key)


def _sync_key_to_dotenv(key: str) -> None:
    """Best-effort write CYCLICAL_COPE_API_KEY into repo .env (host / bind mounts)."""
    try:
        env_path = Path(__file__).resolve().parents[3] / ".env"
        line = f"CYCLICAL_COPE_API_KEY={key}"
        if env_path.is_file():
            text = env_path.read_text(encoding="utf-8")
            if "CYCLICAL_COPE_API_KEY=" in text:
                import re

                text = re.sub(r"(?m)^CYCLICAL_COPE_API_KEY=.*$", line, text)
            else:
                text = text.rstrip() + "\n\n# FOMO Ghost (Cope Capital)\n" + line + "\n"
            env_path.write_text(text, encoding="utf-8")
        else:
            env_path.write_text(f"# FOMO Ghost (Cope Capital)\n{line}\n", encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not sync Cope key to .env: %s", exc)


def effective_api_key() -> str:
    return resolve_cope_api_key() or load_persisted_key()


async def get_fomo_status() -> dict[str, Any]:
    await fomo_db.init_fomo_db()
    key = effective_api_key()
    mode = (await fomo_db.get_state("mode") or "idle").strip().lower()
    if mode not in ("live", "degraded", "idle"):
        mode = "idle"
    traders_count = len(await fomo_db.list_top_traders(_top_n()))
    # Degraded buffer keeps the desk usable without a Cope key while upstream is down.
    needs_key = not bool(key) and mode not in ("degraded", "live") and traders_count == 0
    last_tick = await fomo_db.get_state("last_tick_at")
    last_error = await fomo_db.get_state("last_error") or ""
    degraded_reason = await fomo_db.get_state("last_degraded_reason") or ""
    if mode == "degraded":
        if not degraded_reason and last_error:
            degraded_reason = (
                humanize_cope_error(last_error) if is_cope_unreachable(last_error) else last_error
            )
        last_error = ""
    elif last_error and is_cope_unreachable(last_error):
        last_error = humanize_cope_error(last_error)
    poll_since = await fomo_db.get_state("poll_since")
    usage: dict = {}
    if key and mode == "live":
        try:
            usage = await CopeClient(key).account_usage()
        except Exception:
            usage = {}
    enabled = bool(_fomo_enabled() and (mode in ("live", "degraded") or (key and not needs_key)))
    source = (
        "offline buffer (Cope unreachable)"
        if mode == "degraded"
        else "cope.capital / fomo.family"
    )
    return {
        "enabled": enabled,
        "mode": mode,
        "needs_api_key": needs_key,
        "top_n": _top_n(),
        "timeframe": _timeframe(),
        "interval_seconds": int(getattr(settings, "fomo_interval_seconds", 60) or 60),
        "last_tick_at": last_tick,
        "last_error": last_error or None,
        "degraded": mode == "degraded",
        "degraded_reason": (degraded_reason or None) if mode == "degraded" else None,
        "poll_since": int(poll_since) if poll_since and str(poll_since).isdigit() else None,
        "traders_count": traders_count,
        "events_count": await fomo_db.events_count(),
        "source": source,
        "usage": usage,
        "has_api_key": bool(key),
    }


async def list_fomo_top(limit: int | None = None) -> list[dict]:
    await fomo_db.init_fomo_db()
    return await fomo_db.list_top_traders(limit or _top_n())


async def list_fomo_events(limit: int = 50, side: str | None = None) -> list[dict]:
    await fomo_db.init_fomo_db()
    return await fomo_db.list_events(limit=limit, side=side)


async def register_cope_key(agent_name: str = "cyclical-trader-fomo-ghost") -> dict:
    """One-shot register with Cope; persist key locally (not committed)."""
    client = CopeClient("")
    data = await client.register(agent_name=agent_name)
    key = str(data.get("api_key") or "")
    if not key:
        raise RuntimeError(f"Cope register returned no api_key: {data}")
    persist_api_key(key)
    # Also set on settings for this process if mutable
    try:
        settings.cope_api_key = key  # type: ignore[attr-defined]
    except Exception:
        pass
    await fomo_db.init_fomo_db()
    await fomo_db.set_state("registered_at", datetime.now(timezone.utc).isoformat())
    return {
        "ok": True,
        "api_key_saved": True,
        "hint": "Key saved to backend/data/cope_api_key.txt — prefer CYCLICAL_COPE_API_KEY in .env for Docker",
        "key_prefix": key[:12] + "…",
    }


def filter_activity_to_top(
    activity: list[dict],
    handles: set[str],
) -> list[dict]:
    """Normalize and keep buy/sell for top handles only."""
    out: list[dict] = []
    for row in activity:
        ev = normalize_activity(row)
        if not ev:
            continue
        if ev["handle"].lower() not in handles:
            continue
        if ev["action"] not in ("buy", "sell"):
            continue
        out.append(ev)
    return out


async def run_degraded_tick(*, reason: str = "") -> dict[str, Any]:
    """Local ghost buffer so /fomo stays usable while Cope tunnel is down."""
    await fomo_db.init_fomo_db()
    now_ts = int(time.time())
    now_iso = datetime.now(timezone.utc).isoformat()
    traders = seed_traders(_top_n())
    await fomo_db.replace_top_traders(traders)
    handles = [t["handle"] for t in traders]
    bag = seed_bag_events(handles, now_ts=now_ts, n=4)
    new_buys: list[dict] = []
    inserted = 0
    for ev in bag:
        is_new = await fomo_db.insert_event(ev)
        if not is_new:
            continue
        inserted += 1
        new_buys.append(
            {
                "handle": ev["handle"],
                "action": ev["action"],
                "symbol": ev["symbol"],
                "mint": ev["mint"],
                "chain": ev["chain"],
                "usd_amount": ev.get("usd_amount"),
                "ts_unix": ev.get("ts_unix"),
            }
        )

    hint = humanize_cope_error(reason) if reason else (
        "Cope Capital API offline — degraded ghost buffer active."
    )
    await fomo_db.set_state("mode", "degraded")
    await fomo_db.set_state("last_degraded_reason", hint)
    await fomo_db.set_state("last_error", "")
    await fomo_db.set_state("last_tick_at", now_iso)

    payload = {
        "traders": len(traders),
        "new_buys": new_buys[:20],
        "new_sells": [],
        "inserted": inserted,
        "top_handles": handles[:30],
        "at": now_iso,
        "mode": "degraded",
    }
    try:
        await broadcaster.publish("fomo_tick", payload)
    except Exception as exc:
        logger.debug("fomo_tick publish failed: %s", exc)

    logger.warning("FOMO Ghost degraded tick: top=%d inserted=%d (%s)", len(traders), inserted, hint[:120])
    return {
        "ok": True,
        "mode": "degraded",
        "traders": len(traders),
        "poll_count": 0,
        "activity_fetched": False,
        "new_buys": new_buys,
        "new_sells": [],
        "inserted": inserted,
        "upstream_error": hint,
    }


async def run_fomo_tick(*, force_activity: bool = False) -> dict[str, Any]:
    """One ghost tick: live Cope path, or degraded buffer if upstream is down."""
    await fomo_db.init_fomo_db()
    if not _fomo_enabled():
        return {"ok": False, "reason": "disabled"}

    key = effective_api_key()
    if not key:
        try:
            reg = await register_cope_key()
            key = effective_api_key()
            if key:
                logger.info("FOMO Ghost auto-registered Cope key (%s)", reg.get("key_prefix"))
        except Exception as exc:
            logger.warning("FOMO Ghost auto-register failed: %s", exc)
            if is_cope_unreachable(exc):
                return await run_degraded_tick(reason=str(exc))
            return await run_degraded_tick(reason=str(exc))

    if not key:
        return await run_degraded_tick(reason="COPE_API_KEY missing and register returned empty key")

    client = CopeClient(key)
    now_iso = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {
        "ok": True,
        "mode": "live",
        "traders": 0,
        "poll_count": 0,
        "activity_fetched": False,
        "new_buys": [],
        "new_sells": [],
        "inserted": 0,
    }

    try:
        # 1) Leaderboard (free)
        board = await client.leaderboard(timeframe=_timeframe(), limit=_top_n())
        traders = []
        for i, row in enumerate(board[: _top_n()], start=1):
            t = normalize_trader(row, i)
            if t["handle"]:
                traders.append(t)
        if traders:
            await fomo_db.replace_top_traders(traders)
        result["traders"] = len(traders)
        handles = {t["handle"].lower() for t in traders}

        # 2) Poll (free)
        since_raw = await fomo_db.get_state("poll_since")
        since = int(since_raw) if since_raw and str(since_raw).isdigit() else None
        # First run: seed cursor near now to avoid backfilling the entire history in one paid call
        if since is None:
            since = int(time.time()) - 3600
            await fomo_db.set_state("poll_since", str(since))

        poll = await client.activity_poll(since=since)
        count = int(poll.get("count") or 0)
        latest_at = poll.get("latest_at")
        result["poll_count"] = count

        new_buys: list[dict] = []
        new_sells: list[dict] = []
        inserted = 0

        if count > 0 or force_activity:
            # 3) Activity (counted) — one call, filter to top-30
            rows = await client.activity(since=since)
            result["activity_fetched"] = True
            filtered = filter_activity_to_top(rows, handles)
            for ev in filtered:
                is_new = await fomo_db.insert_event(ev)
                if not is_new:
                    continue
                inserted += 1
                slim = {
                    "handle": ev["handle"],
                    "action": ev["action"],
                    "symbol": ev["symbol"],
                    "mint": ev["mint"],
                    "chain": ev["chain"],
                    "usd_amount": ev.get("usd_amount"),
                    "ts_unix": ev.get("ts_unix"),
                }
                if ev["action"] == "buy":
                    new_buys.append(slim)
                else:
                    new_sells.append(slim)

            # Advance cursor
            if latest_at is not None:
                try:
                    new_since = int(latest_at)
                    if new_since > 10_000_000_000:
                        new_since //= 1000
                    await fomo_db.set_state("poll_since", str(new_since))
                except (TypeError, ValueError):
                    await fomo_db.set_state("poll_since", str(int(time.time())))
            elif filtered:
                max_ts = max(int(e.get("ts_unix") or 0) for e in filtered)
                if max_ts:
                    await fomo_db.set_state("poll_since", str(max_ts))

        result["new_buys"] = new_buys
        result["new_sells"] = new_sells
        result["inserted"] = inserted
        await fomo_db.set_state("mode", "live")
        await fomo_db.set_state("last_tick_at", now_iso)
        await fomo_db.set_state("last_error", "")

        payload = {
            "traders": result["traders"],
            "new_buys": new_buys[:20],
            "new_sells": new_sells[:10],
            "inserted": inserted,
            "top_handles": sorted(handles)[:30],
            "at": now_iso,
            "mode": "live",
        }
        try:
            await broadcaster.publish("fomo_tick", payload)
        except Exception as exc:
            logger.debug("fomo_tick publish failed: %s", exc)

        logger.info(
            "FOMO Ghost tick: top=%d poll=%d activity=%s inserted=%d buys=%d",
            result["traders"],
            count,
            result["activity_fetched"],
            inserted,
            len(new_buys),
        )
        return result

    except Exception as exc:
        logger.warning("FOMO Ghost live tick failed: %s", exc)
        if is_cope_unreachable(exc):
            return await run_degraded_tick(reason=str(exc))
        msg = humanize_cope_error(exc)
        await fomo_db.set_state("last_error", msg)
        await fomo_db.set_state("last_tick_at", now_iso)
        # Keep desk alive with buffer rather than empty error page
        return await run_degraded_tick(reason=str(exc))
