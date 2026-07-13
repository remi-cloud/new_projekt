"""Paper trade execution at live scanner prices."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.data.assets import MONITORED_ASSETS
from app.paper import paper_db
from app.paper.currency import get_usd_pln_rate, native_currency, to_pln
from app.paper.pricing import PaperTradeError, get_live_price
from app.scanners.opportunity_scanner import scanner

logger = logging.getLogger(__name__)

ASSET_MAP = {a["symbol"]: a for a in MONITORED_ASSETS}
TRADE_FEE_RATE = 0.001  # 0.1%


def _get_live_price(symbol: str) -> tuple[float, str]:
    return get_live_price(symbol)


def _round_qty(qty: float, asset_class: str) -> float:
    if asset_class == "crypto":
        return round(qty, 6)
    if asset_class in ("stock", "etf", "index", "bond"):
        return round(qty, 4)
    return round(qty, 2)


def _realized_on_close_long(
    avg_native: float, close_qty: float, close_proceeds_pln: float, currency: str, usd_pln: float
) -> float:
    cost_basis_pln = to_pln(avg_native, currency, usd_pln) * close_qty
    return close_proceeds_pln - cost_basis_pln


def _realized_on_cover_short(
    avg_native: float, cover_qty: float, cover_cost_pln: float, currency: str, usd_pln: float
) -> float:
    entry_pln = to_pln(avg_native, currency, usd_pln) * cover_qty
    return entry_pln - cover_cost_pln


def _new_avg_short(old_qty: float, old_avg: float, add_qty: float, price: float) -> float:
    old_abs = abs(old_qty)
    return (old_abs * old_avg + add_qty * price) / (old_abs + add_qty)


def _position_after_sell(
    held: float, avg_native: float, quantity: float, price_native: float
) -> tuple[float, float]:
    new_qty = held - quantity
    if abs(new_qty) < 1e-9:
        return 0.0, price_native
    if new_qty > 0:
        return new_qty, avg_native
    if held > 0:
        return new_qty, price_native
    if held < 0:
        return new_qty, _new_avg_short(held, avg_native, quantity, price_native)
    return new_qty, price_native


def _position_after_buy(
    held: float, avg_native: float, quantity: float, price_native: float
) -> tuple[float, float]:
    new_qty = held + quantity
    if abs(new_qty) < 1e-9:
        return 0.0, price_native
    if new_qty < 0:
        return new_qty, avg_native
    if held < 0:
        return new_qty, price_native
    if held > 0:
        return new_qty, ((held * avg_native) + (quantity * price_native)) / new_qty
    return new_qty, price_native


async def place_order(
    symbol: str, side: str, quantity: float | None = None, amount_pln: float | None = None
) -> dict:
    if symbol not in ASSET_MAP:
        raise PaperTradeError(f"Instrument {symbol} nie jest monitorowany", "invalid_symbol")
    if side not in ("buy", "sell"):
        raise PaperTradeError("Strona musi być buy lub sell", "invalid_side")
    if quantity is not None and quantity <= 0:
        raise PaperTradeError("Ilość musi być > 0", "invalid_quantity")

    meta = ASSET_MAP[symbol]
    asset_class = meta["asset_class"]

    if amount_pln is not None:
        price_native, currency = _get_live_price(symbol)
        usd_pln = await get_usd_pln_rate()
        price_pln = to_pln(price_native, currency, usd_pln)
        if price_pln <= 0:
            raise PaperTradeError("Nieprawidłowa cena", "no_price")
        if side == "buy":
            denom = price_pln * (1 + TRADE_FEE_RATE)
            quantity = amount_pln / denom
        else:
            quantity = amount_pln / price_pln

    if quantity is None:
        raise PaperTradeError("Podaj quantity lub amount_pln", "invalid_quantity")

    quantity = _round_qty(quantity, asset_class)
    if quantity <= 0:
        raise PaperTradeError("Ilość za mała po zaokrągleniu", "invalid_quantity")

    price_native, currency = _get_live_price(symbol)
    usd_pln = await get_usd_pln_rate()
    price_pln = to_pln(price_native, currency, usd_pln)
    gross_pln = price_pln * quantity
    fee_pln = gross_pln * TRADE_FEE_RATE
    total_pln = gross_pln + fee_pln if side == "buy" else gross_pln - fee_pln

    account = await paper_db.get_account()
    cash = float(account["cash_pln"])
    position = await paper_db.get_position(symbol)
    now = datetime.now(timezone.utc).isoformat()

    if side == "buy":
        if total_pln > cash + 0.01:
            max_qty = (cash * 0.999) / (price_pln * (1 + TRADE_FEE_RATE))
            raise PaperTradeError(
                f"Za mało środków. Masz {cash:,.0f} PLN, koszt {total_pln:,.0f} PLN. "
                f"Max ilość: {_round_qty(max_qty, asset_class)}",
                "insufficient_cash",
            )
        held = float(position["quantity"]) if position else 0.0
        old_avg = float(position["avg_price_native"]) if position else price_native

        realized = 0.0
        if held < 0:
            cover_qty = min(abs(held), quantity)
            if cover_qty > 0:
                cover_cost_pln = total_pln * (cover_qty / quantity)
                realized = _realized_on_cover_short(old_avg, cover_qty, cover_cost_pln, currency, usd_pln)

        new_cash = cash - total_pln
        new_qty, new_avg = _position_after_buy(held, old_avg, quantity, price_native)
        await paper_db.update_account_cash(new_cash, realized_pnl_delta=realized)
        if abs(new_qty) < 1e-9:
            await paper_db.delete_position(symbol)
        else:
            await paper_db.upsert_position(
                symbol, meta["name"], asset_class, new_qty, new_avg, currency
            )
    else:
        held = float(position["quantity"]) if position else 0.0
        old_avg = float(position["avg_price_native"]) if position else price_native
        proceeds = gross_pln - fee_pln

        close_long_qty = min(max(held, 0.0), quantity)
        realized = 0.0
        if close_long_qty > 0:
            close_proceeds = proceeds * (close_long_qty / quantity)
            realized = _realized_on_close_long(old_avg, close_long_qty, close_proceeds, currency, usd_pln)

        new_cash = cash + proceeds
        new_qty, new_avg = _position_after_sell(held, old_avg, quantity, price_native)
        await paper_db.update_account_cash(new_cash, realized_pnl_delta=realized)
        if abs(new_qty) < 1e-9:
            await paper_db.delete_position(symbol)
        else:
            await paper_db.upsert_position(
                symbol, meta["name"], asset_class, new_qty, new_avg, currency
            )

    trade = {
        "symbol": symbol,
        "name": meta["name"],
        "asset_class": asset_class,
        "side": side,
        "quantity": quantity,
        "price_native": price_native,
        "price_pln": round(price_pln, 4),
        "total_pln": round(total_pln if side == "buy" else gross_pln - fee_pln, 2),
        "fee_pln": round(fee_pln, 2),
        "currency": currency,
        "created_at": now,
    }
    await paper_db.insert_trade(trade)
    from app.paper.portfolio_agent import sync_after_trade

    await sync_after_trade()
    logger.info("Paper %s %s x %s @ %s PLN", side, quantity, symbol, price_pln)
    return trade


async def max_buy_quantity(symbol: str) -> float:
    meta = ASSET_MAP.get(symbol)
    if not meta:
        return 0.0
    try:
        price_native, currency = _get_live_price(symbol)
    except PaperTradeError:
        return 0.0
    usd_pln = await get_usd_pln_rate()
    price_pln = to_pln(price_native, currency, usd_pln)
    account = await paper_db.get_account()
    cash = float(account["cash_pln"])
    if price_pln <= 0:
        return 0.0
    qty = (cash * 0.999) / (price_pln * (1 + TRADE_FEE_RATE))
    return _round_qty(qty, meta["asset_class"])


async def close_position(symbol: str) -> dict:
    """Close entire long (sell) or short (buy/cover) position."""
    if symbol not in ASSET_MAP:
        raise PaperTradeError(f"Instrument {symbol} nie jest monitorowany", "invalid_symbol")
    position = await paper_db.get_position(symbol)
    if not position:
        raise PaperTradeError(f"Brak otwartej pozycji na {symbol}", "no_position")
    qty = float(position["quantity"])
    if abs(qty) < 1e-9:
        raise PaperTradeError(f"Brak otwartej pozycji na {symbol}", "no_position")
    meta = ASSET_MAP[symbol]
    abs_qty = _round_qty(abs(qty), meta["asset_class"])
    side = "sell" if qty > 0 else "buy"
    return await place_order(symbol, side, quantity=abs_qty)
