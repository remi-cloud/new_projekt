"""FOMO Family bags — reconstruct open/closed positions from buy/sell activity."""

from __future__ import annotations

from typing import Any

from app.db.sqlite import db_session
from app.fomo import db as fomo_db


async def _load_events_chrono(limit: int = 8000) -> list[dict]:
    """Oldest → newest so net bags accumulate correctly."""
    await fomo_db.init_fomo_db()
    async with db_session() as db:
        cur = await db.execute(
            """
            SELECT handle, action, mint, symbol, chain, usd_amount, ts_unix
            FROM fomo_events
            ORDER BY ts_unix ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
    return [
        {
            "handle": r[0],
            "action": r[1],
            "mint": r[2],
            "symbol": r[3],
            "chain": r[4],
            "usd_amount": r[5],
            "ts_unix": r[6],
        }
        for r in rows
    ]


def reconstruct_bags_from_events(
    events: list[dict],
    *,
    include_closed: bool = True,
) -> list[dict]:
    """Net buy−sell USD per (handle, mint). Status open if net > 0 or last side buy."""
    bags: dict[tuple[str, str], dict[str, Any]] = {}
    for ev in events:
        handle = str(ev.get("handle") or "").strip().lstrip("@").lower()
        mint = str(ev.get("mint") or "").strip()
        if not handle or not mint:
            continue
        key = (handle, mint)
        b = bags.get(key)
        if b is None:
            b = {
                "handle": handle,
                "mint": mint,
                "symbol": str(ev.get("symbol") or "?"),
                "chain": str(ev.get("chain") or "solana"),
                "buys": 0,
                "sells": 0,
                "buy_usd": 0.0,
                "sell_usd": 0.0,
                "last_ts": 0,
                "last_action": None,
            }
            bags[key] = b
        usd = float(ev.get("usd_amount") or 0) or 0.0
        action = str(ev.get("action") or "").lower()
        if action == "buy":
            b["buys"] += 1
            b["buy_usd"] += usd
        elif action == "sell":
            b["sells"] += 1
            b["sell_usd"] += usd
        else:
            continue
        if ev.get("symbol"):
            b["symbol"] = str(ev["symbol"])
        if ev.get("chain"):
            b["chain"] = str(ev["chain"])
        ts = int(ev.get("ts_unix") or 0)
        if ts >= int(b["last_ts"] or 0):
            b["last_ts"] = ts
            b["last_action"] = action

    out: list[dict] = []
    for b in bags.values():
        net = float(b["buy_usd"]) - float(b["sell_usd"])
        # Heuristic: open if net positive, or more buys than sells, or last action buy with residual
        open_bag = net > 1.0 or (b["buys"] > b["sells"]) or (
            b["last_action"] == "buy" and net >= 0
        )
        status = "open" if open_bag else "closed"
        if not include_closed and status != "open":
            continue
        out.append(
            {
                "handle": b["handle"],
                "mint": b["mint"],
                "symbol": b["symbol"],
                "chain": b["chain"],
                "status": status,
                "net_usd": round(net, 2),
                "buy_usd": round(float(b["buy_usd"]), 2),
                "sell_usd": round(float(b["sell_usd"]), 2),
                "buys": b["buys"],
                "sells": b["sells"],
                "last_ts": b["last_ts"] or None,
                "last_action": b["last_action"],
                "family": "fomo.family",
            }
        )

    out.sort(
        key=lambda x: (
            0 if x["status"] == "open" else 1,
            -(abs(float(x.get("net_usd") or 0))),
            x.get("handle") or "",
        )
    )
    return out


async def list_family_bags(
    *,
    include_closed: bool = True,
    limit: int = 300,
    handle: str | None = None,
) -> list[dict]:
    events = await _load_events_chrono(limit=8000)
    bags = reconstruct_bags_from_events(events, include_closed=include_closed)
    if handle:
        h = handle.strip().lstrip("@").lower()
        bags = [b for b in bags if b["handle"] == h]
    return bags[: max(1, limit)]


async def family_summary() -> dict[str, Any]:
    bags = await list_family_bags(include_closed=True, limit=2000)
    open_bags = [b for b in bags if b["status"] == "open"]
    handles = {b["handle"] for b in bags}
    return {
        "family": "fomo.family",
        "traders_with_bags": len(handles),
        "positions_open": len(open_bags),
        "positions_all": len(bags),
        "open_usd_approx": round(sum(float(b.get("net_usd") or 0) for b in open_bags), 2),
    }
