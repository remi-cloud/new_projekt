import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    PaperCloseRequest,
    PaperOrderRequest,
    PaperPortfolio,
    PaperPositionView,
    PaperTradeView,
)
from app.paper.executor import close_position, max_buy_quantity, place_order
from app.paper.limit_orders import cancel_all_pending_orders, cancel_limit_order, place_open_order
from app.paper.paper_db import reset_account
from app.paper.portfolio_agent import sync_after_trade
from app.paper.portfolio_service import build_portfolio, get_position_for_symbol
from app.paper.pricing import PaperTradeError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["paper"])


@router.get("/api/paper/portfolio", response_model=PaperPortfolio)
async def paper_portfolio():
    """Mark-to-market from scanner cache only.

    Do not await live Yahoo/Investing refresh here — those share semaphores with
    the full-market scan and curl_cffi calls are not reliably cancellable, which
    made this endpoint hang and look like the whole server was down.
    """
    data = await build_portfolio()
    return PaperPortfolio(**data)


@router.get("/api/paper/max-buy/{symbol:path}")
async def paper_max_buy(symbol: str):
    qty = await max_buy_quantity(symbol)
    return {"symbol": symbol, "max_quantity": qty}


@router.get("/api/paper/trades/{symbol:path}", response_model=list[PaperTradeView])
async def paper_trades_for_symbol(symbol: str, limit: int = 200):
    from app.paper.paper_db import get_trades_for_symbol

    rows = await get_trades_for_symbol(symbol, limit=limit)
    return [PaperTradeView(**r) for r in rows]


@router.get("/api/paper/position/{symbol:path}", response_model=PaperPositionView)
async def paper_position(symbol: str):
    pos = await get_position_for_symbol(symbol)
    if not pos:
        raise HTTPException(status_code=404, detail="Brak otwartej pozycji")
    return PaperPositionView(**pos)


@router.post("/api/paper/close/{symbol:path}")
async def paper_close_position(symbol: str, body: PaperCloseRequest | None = None):
    percent = body.percent if body else 100.0
    try:
        trade = await close_position(symbol, percent=percent)
        portfolio = await build_portfolio()
        return {"trade": trade, "portfolio": portfolio}
    except PaperTradeError as exc:
        raise HTTPException(status_code=400, detail={"message": exc.message, "code": exc.code}) from None


@router.post("/api/paper/order")
async def paper_order(body: PaperOrderRequest):
    # Never await a full market scan here — that blocked pearl / ad-hoc trades for minutes.
    try:
        if body.order_type in ("limit", "stop", "take_profit"):
            if body.limit_price_native is None:
                raise PaperTradeError("Podaj limit_price_native (cena trigger)", "invalid_limit_price")
            result = await place_open_order(
                body.symbol,
                body.side,
                body.order_type,
                body.limit_price_native,
                amount_pln=body.amount_pln,
                quantity=body.quantity,
            )
            portfolio = await build_portfolio()
            return {**result, "portfolio": portfolio}

        trade = await place_order(
            body.symbol, body.side, quantity=body.quantity, amount_pln=body.amount_pln
        )
        portfolio = await build_portfolio()
        return {"status": "filled", "order_type": "market", "trade": trade, "portfolio": portfolio}
    except PaperTradeError as exc:
        raise HTTPException(status_code=400, detail={"message": exc.message, "code": exc.code}) from None


@router.delete("/api/paper/limit/{order_id}")
async def paper_cancel_limit(order_id: int):
    try:
        await cancel_limit_order(order_id)
        portfolio = await build_portfolio()
        return {"status": "cancelled", "portfolio": portfolio}
    except PaperTradeError as exc:
        raise HTTPException(status_code=400, detail={"message": exc.message, "code": exc.code}) from None


@router.delete("/api/paper/orders/{order_id}")
async def paper_cancel_order(order_id: int):
    return await paper_cancel_limit(order_id)


@router.post("/api/paper/orders/cancel-all")
async def paper_cancel_all_orders(symbol: str | None = None):
    try:
        count = await cancel_all_pending_orders(symbol)
        portfolio = await build_portfolio()
        return {"status": "cancelled", "count": count, "portfolio": portfolio}
    except PaperTradeError as exc:
        raise HTTPException(status_code=400, detail={"message": exc.message, "code": exc.code}) from None


@router.post("/api/paper/reset")
async def paper_reset():
    await reset_account()
    await sync_after_trade()
    return await build_portfolio()


@router.get("/api/paper/ledger/status")
async def paper_ledger_status():
    """Disk ledger vs SQLite — path, trade counts, last ts, ok/drift."""
    from app.paper.ledger_agent import ledger_status

    return await ledger_status()


@router.post("/api/paper/purge-agent-positions")
async def paper_purge_agent_positions(force: bool = False):
    """Close positions created by execution agent (dry-run mirror), not manual user orders."""
    from app.paper.cleanup import purge_execution_agent_positions

    result = await purge_execution_agent_positions(force=force)
    portfolio = await build_portfolio()
    return {**result, "portfolio": portfolio}
