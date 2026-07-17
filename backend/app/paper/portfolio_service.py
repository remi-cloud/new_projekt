"""Build paper portfolio view with mark-to-market."""

from __future__ import annotations

from app.data.broker_map import resolve_broker_info
from app.paper import paper_db
from app.paper.currency import get_usd_pln_rate, native_currency, to_pln
from app.paper.limit_orders import limit_orders_for_portfolio
from app.paper.pricing import get_live_price, refresh_quotes_for_symbols
from app.scanners.opportunity_scanner import scanner


class PaperTradeError(Exception):
    pass


async def _position_to_view(pos: dict, usd_pln: float) -> dict:
    symbol = pos["symbol"]
    qty = float(pos["quantity"])
    avg_native = float(pos["avg_price_native"])
    currency = pos["currency"] or native_currency(symbol)
    asset_class = pos["asset_class"]

    # Cache-only for list views — never block HTTP on Investing/Yahoo here.
    try:
        current_native, _ = get_live_price(symbol)
    except Exception:
        current_native = avg_native

    current_pln = to_pln(current_native, currency, usd_pln)
    avg_pln = to_pln(avg_native, currency, usd_pln)
    market_value = current_pln * qty
    cost_basis = avg_pln * qty
    unrealized = market_value - cost_basis
    unrealized_pct = (unrealized / cost_basis * 100) if cost_basis > 0 else 0.0

    region = None
    try:
        assessment = next((a for a in scanner.market_assessments if a.symbol == symbol), None)
        if assessment:
            region = getattr(assessment, "region", None)
            if hasattr(region, "value"):
                region = region.value
    except Exception:
        region = None

    return {
        "symbol": symbol,
        "name": pos["name"],
        "asset_class": asset_class,
        "quantity": qty,
        "is_short": qty < 0,
        "avg_price_native": avg_native,
        "avg_price_pln": round(avg_pln, 4),
        "current_price_native": current_native,
        "current_price_pln": round(current_pln, 4),
        "market_value_pln": round(market_value, 2),
        "cost_basis_pln": round(cost_basis, 2),
        "unrealized_pnl_pln": round(unrealized, 2),
        "unrealized_pnl_pct": round(unrealized_pct, 2),
        "currency": currency,
        "opened_at": pos.get("opened_at"),
        "broker_info": resolve_broker_info(symbol, str(asset_class), region),
    }


async def get_position_for_symbol(symbol: str) -> dict | None:
    pos = await paper_db.get_position(symbol)
    if not pos or abs(float(pos["quantity"])) < 1e-9:
        return None
    await refresh_quotes_for_symbols([symbol])
    usd_pln = await get_usd_pln_rate()
    view = await _position_to_view(pos, usd_pln)
    limits = await limit_orders_for_portfolio()
    view["pending_limit_orders"] = [lo for lo in limits if lo["symbol"] == symbol]
    return view


async def build_portfolio() -> dict:
    account = await paper_db.get_account()
    positions_raw = await paper_db.get_positions()
    trades = await paper_db.get_trades(limit=30)
    closed_raw = await paper_db.get_closed_positions(limit=50)
    limit_orders = await limit_orders_for_portfolio()
    usd_pln = await get_usd_pln_rate(allow_network=False)
    limits_by_symbol: dict[str, list] = {}
    for lo in limit_orders:
        limits_by_symbol.setdefault(lo["symbol"], []).append(lo)

    positions = []
    positions_value = 0.0
    unrealized_total = 0.0

    for pos in positions_raw:
        view = await _position_to_view(pos, usd_pln)
        view["pending_limit_orders"] = limits_by_symbol.get(view["symbol"], [])
        qty = view["quantity"]
        positions_value += view["market_value_pln"]
        unrealized_total += view["unrealized_pnl_pln"]
        positions.append(view)

    cash = float(account["cash_pln"])
    initial = float(account["initial_cash_pln"])
    realized = float(account.get("realized_pnl_pln") or 0)
    total_equity = cash + positions_value

    closed_positions = [
        {
            "id": c["id"],
            "symbol": c["symbol"],
            "name": c["name"],
            "asset_class": c["asset_class"],
            "quantity": c["quantity"],
            "is_short": c["is_short"],
            "entry_price_native": c["entry_price_native"],
            "exit_price_native": c["exit_price_native"],
            "entry_price_pln": c["entry_price_pln"],
            "exit_price_pln": c["exit_price_pln"],
            "cost_basis_pln": c["cost_basis_pln"],
            "proceeds_pln": c["proceeds_pln"],
            "realized_pnl_pln": c["realized_pnl_pln"],
            "realized_pnl_pct": c["realized_pnl_pct"],
            "currency": c["currency"],
            "opened_at": c["opened_at"],
            "closed_at": c["closed_at"],
        }
        for c in closed_raw
    ]

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
        "closed_positions_count": len(closed_positions),
        "closed_positions": closed_positions,
        "limit_orders": limit_orders,
        "recent_trades": trades,
        "quotes_available": len(scanner.quotes),
    }
