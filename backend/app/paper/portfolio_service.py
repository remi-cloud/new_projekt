"""Build paper portfolio view with mark-to-market."""

from __future__ import annotations

from app.paper import paper_db
from app.paper.currency import get_usd_pln_rate, native_currency, to_pln
from app.paper.executor import _get_live_price
from app.scanners.opportunity_scanner import scanner


class PaperTradeError(Exception):
    pass


async def build_portfolio() -> dict:
    account = await paper_db.get_account()
    positions_raw = await paper_db.get_positions()
    trades = await paper_db.get_trades(limit=30)
    usd_pln = await get_usd_pln_rate()

    positions = []
    positions_value = 0.0
    unrealized_total = 0.0

    for pos in positions_raw:
        symbol = pos["symbol"]
        qty = float(pos["quantity"])
        avg_native = float(pos["avg_price_native"])
        currency = pos["currency"] or native_currency(symbol)

        try:
            current_native, _ = _get_live_price(symbol)
        except Exception:
            current_native = avg_native

        current_pln = to_pln(current_native, currency, usd_pln)
        avg_pln = to_pln(avg_native, currency, usd_pln)
        market_value = current_pln * qty
        cost_basis = avg_pln * qty
        unrealized = market_value - cost_basis
        unrealized_pct = (unrealized / cost_basis * 100) if cost_basis > 0 else 0.0

        positions_value += market_value
        unrealized_total += unrealized

        positions.append({
            "symbol": symbol,
            "name": pos["name"],
            "asset_class": pos["asset_class"],
            "quantity": qty,
            "avg_price_native": avg_native,
            "avg_price_pln": round(avg_pln, 4),
            "current_price_native": current_native,
            "current_price_pln": round(current_pln, 4),
            "market_value_pln": round(market_value, 2),
            "cost_basis_pln": round(cost_basis, 2),
            "unrealized_pnl_pln": round(unrealized, 2),
            "unrealized_pnl_pct": round(unrealized_pct, 2),
            "currency": currency,
        })

    cash = float(account["cash_pln"])
    initial = float(account["initial_cash_pln"])
    realized = float(account.get("realized_pnl_pln") or 0)
    total_equity = cash + positions_value

    return {
        "cash_pln": round(cash, 2),
        "initial_cash_pln": round(initial, 2),
        "positions_value_pln": round(positions_value, 2),
        "total_equity_pln": round(total_equity, 2),
        "unrealized_pnl_pln": round(unrealized_total, 2),
        "realized_pnl_pln": round(realized, 2),
        "total_pnl_pln": round(total_equity - initial, 2),
        "total_pnl_pct": round((total_equity - initial) / initial * 100, 2) if initial else 0,
        "usd_pln_rate": round(usd_pln, 4),
        "positions_count": len(positions),
        "positions": sorted(positions, key=lambda p: p["market_value_pln"], reverse=True),
        "recent_trades": trades,
        "quotes_available": len(scanner.quotes),
    }
