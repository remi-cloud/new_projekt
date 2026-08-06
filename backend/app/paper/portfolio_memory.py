"""Paper portfolio → agent session memory (survives app restart via portfolio.db)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

PORTFOLIO_MEMORY_TOPIC = "paper_portfolio_session"
PORTFOLIO_MEMORY_SOURCE = "portfolio_session"


def compact_portfolio_summary(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Compact mark-to-market view for agent context (no full trade log)."""
    positions = []
    for p in portfolio.get("positions") or []:
        positions.append(
            {
                "symbol": p.get("symbol"),
                "quantity": p.get("quantity"),
                "avg_price": p.get("avg_price") or p.get("avg_entry_price"),
                "market_value_pln": p.get("market_value_pln") or p.get("value_pln"),
                "unrealized_pnl_pln": p.get("unrealized_pnl_pln"),
            }
        )
    recent = []
    for t in (portfolio.get("recent_trades") or [])[:8]:
        recent.append(
            {
                "side": t.get("side"),
                "symbol": t.get("symbol"),
                "quantity": t.get("quantity"),
                "total_pln": t.get("total_pln"),
                "created_at": t.get("created_at"),
            }
        )
    return {
        "cash_pln": portfolio.get("cash_pln"),
        "total_equity_pln": portfolio.get("total_equity_pln"),
        "positions_value_pln": portfolio.get("positions_value_pln"),
        "total_pnl_pln": portfolio.get("total_pnl_pln"),
        "total_pnl_pct": portfolio.get("total_pnl_pct"),
        "positions_count": portfolio.get("positions_count"),
        "positions": positions,
        "recent_trades": recent,
        "initial_cash_pln": portfolio.get("initial_cash_pln"),
    }


def format_portfolio_lesson(summary: dict[str, Any]) -> str:
    cash = float(summary.get("cash_pln") or 0)
    equity = float(summary.get("total_equity_pln") or 0)
    n = int(summary.get("positions_count") or 0)
    pos_bits = []
    for p in summary.get("positions") or []:
        sym = p.get("symbol") or "?"
        qty = p.get("quantity")
        pnl = p.get("unrealized_pnl_pln")
        pos_bits.append(f"{sym} qty={qty} uPnL={pnl}")
    pos_line = "; ".join(pos_bits) if pos_bits else "brak otwartych pozycji"
    trades = summary.get("recent_trades") or []
    trade_line = (
        ", ".join(f"{t.get('side')} {t.get('symbol')}" for t in trades[:5])
        if trades
        else "brak transakcji w tej sesji"
    )
    return (
        f"Paper desk (zapisana sesja z portfolio.db): cash={cash:.0f} PLN, "
        f"equity={equity:.0f} PLN, pozycji={n}. Otwarte: {pos_line}. "
        f"Ostatnie transakcje: {trade_line}. "
        "Trades są real-time w paper; przy restarcie aplikacji wczytaj ten stan — nie zakładaj pustego konta."
    )


async def seed_agent_portfolio_memory(portfolio: dict[str, Any] | None = None) -> dict[str, Any]:
    """Upsert agent memory from live paper portfolio (call on startup + after trades)."""
    from app.ai import db as ai_db
    from app.paper.portfolio_service import build_portfolio

    if portfolio is None:
        portfolio = await build_portfolio()
    summary = compact_portfolio_summary(portfolio)
    lesson = format_portfolio_lesson(summary)
    await ai_db.upsert_learning_note(
        topic=PORTFOLIO_MEMORY_TOPIC,
        lesson=lesson,
        source=PORTFOLIO_MEMORY_SOURCE,
        confidence=0.95,
    )
    logger.info(
        "Agent memory: paper portfolio seeded (cash=%.0f equity=%.0f positions=%s)",
        float(summary.get("cash_pln") or 0),
        float(summary.get("total_equity_pln") or 0),
        summary.get("positions_count"),
    )
    return summary


async def get_agent_portfolio_context() -> dict[str, Any]:
    """Load portfolio for chat/self-learn injection (DB is source of truth)."""
    from app.paper.portfolio_service import build_portfolio

    portfolio = await build_portfolio()
    return compact_portfolio_summary(portfolio)
