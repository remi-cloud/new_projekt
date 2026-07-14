"""Paper open orders: limit, stop-loss, take-profit."""

from __future__ import annotations

import logging

from app.data.assets import MONITORED_ASSETS
from app.paper import paper_db
from app.paper.currency import get_usd_pln_rate, native_currency, to_pln
from app.paper.executor import ASSET_MAP, _round_qty, place_order
from app.paper.pricing import PaperTradeError, get_live_price

logger = logging.getLogger(__name__)

VALID_ORDER_TYPES = ("limit", "stop", "take_profit")


def _order_should_fill(order_type: str, side: str, market_price: float, trigger_price: float) -> bool:
    if order_type == "limit":
        return market_price <= trigger_price if side == "buy" else market_price >= trigger_price
    if order_type == "stop":
        return market_price <= trigger_price if side == "sell" else market_price >= trigger_price
    if order_type == "take_profit":
        return market_price >= trigger_price if side == "sell" else market_price <= trigger_price
    return False


def _order_to_view(order: dict, usd_pln: float) -> dict:
    trigger_native = float(order["limit_price_native"])
    currency = order["currency"]
    trigger_pln = to_pln(trigger_native, currency, usd_pln)
    amount_pln = float(order["amount_pln"])
    asset_class = order["asset_class"]
    side = order["side"]
    order_type = order.get("order_type") or "limit"
    qty_est = (
        amount_pln / (trigger_pln * 1.001)
        if side == "buy" and trigger_pln > 0
        else (amount_pln / trigger_pln if trigger_pln > 0 else 0)
    )
    return {
        "id": order["id"],
        "symbol": order["symbol"],
        "name": order["name"],
        "asset_class": asset_class,
        "side": side,
        "order_type": order_type,
        "limit_price_native": trigger_native,
        "limit_price_pln": round(trigger_pln, 4),
        "amount_pln": amount_pln,
        "quantity_est": _round_qty(qty_est, asset_class),
        "currency": currency,
        "status": order["status"],
        "created_at": order["created_at"],
    }


async def place_open_order(
    symbol: str,
    side: str,
    order_type: str,
    trigger_price_native: float,
    amount_pln: float | None = None,
    quantity: float | None = None,
) -> dict:
    if symbol not in ASSET_MAP:
        raise PaperTradeError(f"Instrument {symbol} nie jest monitorowany", "invalid_symbol")
    if side not in ("buy", "sell"):
        raise PaperTradeError("Strona musi być buy lub sell", "invalid_side")
    if order_type not in VALID_ORDER_TYPES:
        raise PaperTradeError("Typ zlecenia: limit, stop lub take_profit", "invalid_order_type")
    if trigger_price_native <= 0:
        raise PaperTradeError("Cena trigger musi być > 0", "invalid_limit_price")
    if amount_pln is None and quantity is None:
        raise PaperTradeError("Podaj amount_pln lub quantity", "invalid_quantity")
    if amount_pln is not None and amount_pln <= 0:
        raise PaperTradeError("Wartość zamówienia musi być > 0", "invalid_quantity")

    meta = ASSET_MAP[symbol]
    currency = native_currency(symbol)
    usd_pln = await get_usd_pln_rate()
    trigger_pln = to_pln(trigger_price_native, currency, usd_pln)

    if amount_pln is None and quantity is not None:
        gross = trigger_pln * quantity
        amount_pln = gross * (1 + 0.001) if side == "buy" else gross

    assert amount_pln is not None

    market_price, _ = get_live_price(symbol)
    if _order_should_fill(order_type, side, market_price, trigger_price_native):
        trade = await place_order(
            symbol,
            side,
            amount_pln=amount_pln,
            price_native_override=trigger_price_native,
        )
        return {
            "status": "filled",
            "order_type": order_type,
            "trade": trade,
        }

    order = await paper_db.insert_limit_order(
        {
            "symbol": symbol,
            "name": meta["name"],
            "asset_class": meta["asset_class"],
            "side": side,
            "order_type": order_type,
            "limit_price_native": trigger_price_native,
            "amount_pln": round(amount_pln, 2),
            "currency": currency,
        }
    )
    view = _order_to_view(order, usd_pln)
    logger.info("%s %s %s @ %s %s — oczekuje", order_type, side, symbol, trigger_price_native, currency)
    return {"status": "pending", "order_type": order_type, "open_order": view}


async def process_limit_orders() -> int:
    pending = await paper_db.get_pending_limit_orders()
    if not pending:
        return 0

    filled = 0
    for order in pending:
        symbol = order["symbol"]
        side = order["side"]
        order_type = order.get("order_type") or "limit"
        trigger_price = float(order["limit_price_native"])
        amount_pln = float(order["amount_pln"])
        order_id = int(order["id"])

        try:
            market_price, _ = get_live_price(symbol)
        except PaperTradeError:
            continue

        if not _order_should_fill(order_type, side, market_price, trigger_price):
            continue

        try:
            await place_order(
                symbol,
                side,
                amount_pln=amount_pln,
                price_native_override=trigger_price,
            )
            await paper_db.mark_limit_order_filled(order_id)
            filled += 1
            logger.info("Order #%s filled (%s): %s %s @ %s", order_id, order_type, side, symbol, trigger_price)
        except PaperTradeError as exc:
            logger.warning("Order #%s fill failed: %s", order_id, exc.message)

    return filled


async def cancel_limit_order(order_id: int) -> dict:
    order = await paper_db.get_limit_order(order_id)
    if not order:
        raise PaperTradeError("Nie znaleziono zlecenia", "not_found")
    if order["status"] != "pending":
        raise PaperTradeError("Zlecenie nie jest aktywne", "not_pending")
    await paper_db.cancel_limit_order(order_id)
    usd_pln = await get_usd_pln_rate()
    return _order_to_view({**order, "status": "cancelled"}, usd_pln)


async def cancel_all_pending_orders(symbol: str | None = None) -> int:
    pending = await paper_db.get_pending_limit_orders()
    if symbol:
        pending = [o for o in pending if o["symbol"] == symbol]
    count = 0
    for order in pending:
        await paper_db.cancel_limit_order(int(order["id"]))
        count += 1
    return count


async def limit_orders_for_portfolio() -> list[dict]:
    orders = await paper_db.get_pending_limit_orders()
    usd_pln = await get_usd_pln_rate()
    return [_order_to_view(order, usd_pln) for order in orders]


# Backward-compatible alias
place_limit_order = place_open_order
