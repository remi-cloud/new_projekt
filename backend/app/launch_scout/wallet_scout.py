"""Wallet Scout (P0) — open bags + direction for Pump top traders."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.launch_scout import db as launch_db
from app.launch_scout.terminal_url import axiom_meme_url, terminal_url

logger = logging.getLogger(__name__)


def reconstruct_wallet_bags_from_events(
    events: list[dict],
    *,
    include_closed: bool = True,
    wallet: str | None = None,
) -> list[dict]:
    """Net buy−sell USD per (wallet, mint). Mirrors FOMO Family bags for Pump wallets."""
    bags: dict[tuple[str, str], dict[str, Any]] = {}
    want = (wallet or "").strip()
    for ev in events:
        w = str(ev.get("wallet") or "").strip()
        mint = str(ev.get("mint") or "").strip()
        if not w or not mint:
            continue
        if want and w != want:
            continue
        key = (w, mint)
        b = bags.get(key)
        if b is None:
            b = {
                "wallet": w,
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
        open_bag = net > 1.0 or (b["buys"] > b["sells"]) or (
            b["last_action"] == "buy" and net >= 0
        )
        status = "open" if open_bag else "closed"
        if not include_closed and status != "open":
            continue
        chain = str(b["chain"] or "solana")
        mint = str(b["mint"])
        sym = str(b["symbol"] or "?")
        term = terminal_url(mint=mint, symbol=sym, chain=chain) or axiom_meme_url(mint, chain)
        out.append(
            {
                "wallet": b["wallet"],
                "mint": mint,
                "symbol": sym,
                "chain": chain,
                "status": status,
                "side": "long" if net > 0 else ("flat" if abs(net) < 1 else "exited"),
                "net_usd": round(net, 2),
                "buy_usd": round(float(b["buy_usd"]), 2),
                "sell_usd": round(float(b["sell_usd"]), 2),
                "buys": b["buys"],
                "sells": b["sells"],
                "last_ts": b["last_ts"] or None,
                "last_action": b["last_action"],
                "url": term or None,
                "source": "events",
            }
        )

    out.sort(
        key=lambda x: (
            0 if x["status"] == "open" else 1,
            -(abs(float(x.get("net_usd") or 0))),
            x.get("wallet") or "",
        )
    )
    return out


async def list_trader_events_chrono(limit: int = 4000) -> list[dict]:
    """Oldest → newest for bag reconstruction."""
    await launch_db.init_launch_scout_db()
    # list_trader_events is newest-first; reverse for chrono
    rows = await launch_db.list_trader_events(limit=max(1, min(5000, limit)))
    rows = list(reversed(rows))
    return rows


async def list_wallet_bags(
    *,
    wallet: str | None = None,
    include_closed: bool = True,
    limit: int = 200,
) -> list[dict]:
    events = await list_trader_events_chrono(limit=4000)
    bags = reconstruct_wallet_bags_from_events(
        events, include_closed=include_closed, wallet=wallet
    )
    return bags[: max(1, limit)]


async def enrich_holdings_rpc(wallets: list[str], *, per_wallet: int = 12) -> dict[str, list[dict]]:
    """Best-effort SPL holdings for top-N wallets via Solana RPC."""
    from app.axiom.client import fetch_wallet_token_accounts

    out: dict[str, list[dict]] = {}
    for w in wallets:
        try:
            accounts = await fetch_wallet_token_accounts(w)
        except Exception as exc:
            logger.debug("Wallet Scout RPC %s…: %s", w[:8], exc)
            accounts = []
        holdings: list[dict] = []
        for acc in accounts[:per_wallet]:
            mint = str(acc.get("mint") or "")
            if not mint:
                continue
            term = terminal_url(mint=mint, chain="solana") or axiom_meme_url(mint, "solana")
            holdings.append(
                {
                    "mint": mint,
                    "symbol": mint[:6],
                    "chain": "solana",
                    "amount": acc.get("amount"),
                    "decimals": acc.get("decimals"),
                    "url": term or None,
                    "source": "solana_rpc",
                    "status": "open",
                    "side": "long",
                }
            )
        out[w] = holdings
    return out


def _top_n() -> int:
    return max(1, min(30, int(getattr(settings, "wallet_scout_top_n", 15) or 15)))


async def run_wallet_scout(*, traders: list[dict] | None = None) -> dict[str, Any]:
    """
    Build bag summaries for top traders. Call after trader events are persisted.
    Returns telemetry for launch tick / coordinator.
    """
    await launch_db.init_launch_scout_db()
    top_n = _top_n()
    if traders is None:
        traders = await launch_db.list_traders(limit=30)
    wallets = [str(t.get("wallet") or "") for t in traders[:top_n] if t.get("wallet")]

    events = await list_trader_events_chrono(limit=4000)
    all_bags = reconstruct_wallet_bags_from_events(events, include_closed=True)
    by_wallet: dict[str, list[dict]] = {}
    for b in all_bags:
        by_wallet.setdefault(str(b["wallet"]), []).append(b)

    holdings_map: dict[str, list[dict]] = {}
    try:
        holdings_map = await enrich_holdings_rpc(wallets, per_wallet=12)
    except Exception as exc:
        logger.warning("Wallet Scout RPC batch failed: %s", exc)

    enriched_traders: list[dict] = []
    open_total = 0
    for t in traders:
        w = str(t.get("wallet") or "")
        bags = by_wallet.get(w) or []
        open_bags = [b for b in bags if b.get("status") == "open"]
        open_total += len(open_bags)
        holdings = holdings_map.get(w) or []
        last_side = None
        if bags:
            last_side = bags[0].get("last_action")  # sorted open-first; prefer freshest
            freshest = max(bags, key=lambda x: int(x.get("last_ts") or 0))
            last_side = freshest.get("last_action")
        mints = list({str(b["mint"]) for b in bags if b.get("mint")})[:12]
        for h in holdings:
            if h.get("mint") and h["mint"] not in mints:
                mints.append(h["mint"])
        enriched_traders.append(
            {
                **{k: t[k] for k in t if k != "raw"},
                "mints": mints[:12],
                "open_bags": len(open_bags),
                "bags_all": len(bags),
                "last_side": last_side,
                "bags": open_bags[:8],
                "holdings": holdings[:8],
            }
        )

    return {
        "ok": True,
        "top_n": top_n,
        "wallets_scanned": len(wallets),
        "open_bags": open_total,
        "traders": enriched_traders,
    }


async def get_wallet_scout_snapshot(*, limit: int = 15) -> dict[str, Any]:
    """Read-only snapshot for API / Finance Agent / coordinator (from last tick)."""
    await launch_db.init_launch_scout_db()
    lim = max(1, min(30, limit))
    traders = await launch_db.list_traders(limit=lim)
    open_bags = sum(int(t.get("open_bags") or 0) for t in traders)
    return {
        "brand": "Wallet Scout",
        "priority": "P0",
        "top_n": _top_n(),
        "wallets_scanned": len(traders),
        "open_bags": open_bags,
        "traders": traders,
        "note": "Event net bags + optional RPC holdings for top Pump wallets. Educational — not advice.",
    }


async def bags_for_wallet(wallet: str, *, include_closed: bool = True) -> dict[str, Any]:
    w = (wallet or "").strip()
    bags = await list_wallet_bags(wallet=w, include_closed=include_closed, limit=100)
    holdings: list[dict] = []
    try:
        holdings_map = await enrich_holdings_rpc([w], per_wallet=20)
        holdings = holdings_map.get(w) or []
    except Exception:
        holdings = []
    return {
        "wallet": w,
        "bags": bags,
        "holdings": holdings,
        "open_count": sum(1 for b in bags if b.get("status") == "open"),
    }
