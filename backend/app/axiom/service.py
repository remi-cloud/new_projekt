"""Axiom desk service — Pulse tick + all positions (FOMO Family + wallets)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.axiom import client as axiom_client
from app.axiom import db as axiom_db
from app.config import settings
from app.launch_scout.terminal_url import axiom_meme_url
from app.realtime.broadcaster import broadcaster

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(getattr(settings, "axiom_enabled", True))


async def get_axiom_status() -> dict[str, Any]:
    await axiom_db.init_axiom_db()
    last_tick = await axiom_db.get_state("last_tick_at")
    last_error = await axiom_db.get_state("last_error") or ""
    source = await axiom_db.get_state("pulse_source") or "dex"
    return {
        "enabled": _enabled(),
        "brand": "Axiom · Pulse",
        "tagline": "Pulse markets + all bag positions (FOMO Family · wallets)",
        "interval_seconds": int(getattr(settings, "axiom_interval_seconds", 90) or 90),
        "last_tick_at": last_tick,
        "last_error": last_error or None,
        "pulse_count": await axiom_db.pulse_count(),
        "positions_open": await axiom_db.positions_count("open"),
        "positions_all": await axiom_db.positions_count(),
        "pulse_source": source,
        "axiom_auth": axiom_client.axiom_auth_configured(),
        "wallets_tracked": len(axiom_client.tracked_wallets()),
        "kar_digital_wallet": axiom_client.kar_digital_wallet() or None,
        "kar_digital_configured": bool(axiom_client.kar_digital_wallet()),
        "include_closed": bool(getattr(settings, "axiom_include_closed", True)),
    }


async def list_axiom_pulse(limit: int = 80) -> list[dict]:
    await axiom_db.init_axiom_db()
    return await axiom_db.list_pulse(limit=limit)


async def list_axiom_positions(
    *,
    limit: int = 200,
    status: str | None = "open",
    owner_kind: str | None = None,
) -> list[dict]:
    await axiom_db.init_axiom_db()
    return await axiom_db.list_positions(limit=limit, status=status, owner_kind=owner_kind)


async def _collect_pulse() -> tuple[list[dict], str]:
    period = str(getattr(settings, "axiom_trending_period", "1h") or "1h")
    axiom_rows = await axiom_client.fetch_axiom_trending(period)
    if axiom_rows:
        return axiom_rows, "axiom"
    dex_rows = await axiom_client.fetch_dex_pulse(limit=80)
    return dex_rows, "dex"


async def _collect_positions(*, include_closed: bool) -> list[dict]:
    from app.fomo.bags import list_family_bags

    positions: list[dict] = []
    bags = await list_family_bags(include_closed=include_closed, limit=500)
    for b in bags:
        status = b.get("status") or "open"
        if not include_closed and status != "open":
            continue
        handle = str(b.get("handle") or "")
        mint = str(b.get("mint") or "")
        bag_chain = str(b.get("chain") or "solana")
        positions.append(
            {
                "position_id": f"fomo:{handle}:{mint}",
                "owner": handle,
                "owner_kind": "fomo_family",
                "mint": mint,
                "symbol": b.get("symbol") or "?",
                "chain": bag_chain,
                "status": status,
                "usd_size": b.get("net_usd"),
                "amount": None,
                "last_ts": b.get("last_ts"),
                "url": axiom_meme_url(mint, bag_chain) if mint else None,
                "image_url": None,
                "raw": {"buys": b.get("buys"), "sells": b.get("sells"), "source": "fomo_family"},
            }
        )

    for wallet in axiom_client.tracked_wallets():
        accounts = await axiom_client.fetch_wallet_token_accounts(wallet)
        kind = axiom_client.wallet_owner_kind(wallet)
        label = axiom_client.wallet_owner_label(wallet)
        for acc in accounts:
            mint = acc["mint"]
            positions.append(
                {
                    "position_id": f"{kind}:{wallet}:{mint}",
                    "owner": label if kind == "kar_digital" else wallet,
                    "owner_kind": kind,
                    "mint": mint,
                    "symbol": mint[:6],
                    "chain": "solana",
                    "status": "open",
                    "usd_size": None,
                    "amount": acc.get("amount"),
                    "last_ts": None,
                    "url": axiom_meme_url(mint, "solana"),
                    "image_url": None,
                    "raw": {
                        "decimals": acc.get("decimals"),
                        "source": "solana_rpc",
                        "wallet": wallet,
                        "brand": "Kar Digital" if kind == "kar_digital" else None,
                    },
                }
            )

    # Deduplicate by position_id
    seen: set[str] = set()
    uniq: list[dict] = []
    for p in positions:
        pid = p["position_id"]
        if pid in seen:
            continue
        seen.add(pid)
        uniq.append(p)
    return uniq


async def run_axiom_tick() -> dict[str, Any]:
    await axiom_db.init_axiom_db()
    if not _enabled():
        return {"ok": False, "reason": "disabled"}

    now_iso = datetime.now(timezone.utc).isoformat()
    include_closed = bool(getattr(settings, "axiom_include_closed", True))
    result: dict[str, Any] = {
        "ok": True,
        "pulse": 0,
        "positions": 0,
        "positions_open": 0,
        "source": "dex",
    }

    try:
        pulse, source = await _collect_pulse()
        await axiom_db.replace_pulse(pulse)
        result["pulse"] = len(pulse)
        result["source"] = source
        await axiom_db.set_state("pulse_source", source)

        positions = await _collect_positions(include_closed=include_closed)
        await axiom_db.replace_positions(positions)
        result["positions"] = len(positions)
        result["positions_open"] = sum(1 for p in positions if p.get("status") == "open")

        await axiom_db.set_state("last_tick_at", now_iso)
        await axiom_db.set_state("last_error", "")

        payload = {
            "pulse": result["pulse"],
            "positions": result["positions"],
            "positions_open": result["positions_open"],
            "source": source,
            "at": now_iso,
        }
        try:
            await broadcaster.publish("axiom_tick", payload)
        except Exception as exc:
            logger.debug("axiom_tick publish failed: %s", exc)

        logger.info(
            "Axiom tick: pulse=%d positions=%d open=%d source=%s",
            result["pulse"],
            result["positions"],
            result["positions_open"],
            source,
        )
        return result
    except Exception as exc:
        logger.warning("Axiom tick failed: %s", exc)
        await axiom_db.set_state("last_error", str(exc)[:400])
        await axiom_db.set_state("last_tick_at", now_iso)
        return {"ok": False, "error": str(exc)[:400]}
