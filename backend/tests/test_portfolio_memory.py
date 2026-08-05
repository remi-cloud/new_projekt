"""Paper portfolio → agent session memory."""

from unittest.mock import AsyncMock, patch

import pytest

from app.paper.portfolio_memory import (
    PORTFOLIO_MEMORY_SOURCE,
    PORTFOLIO_MEMORY_TOPIC,
    compact_portfolio_summary,
    format_portfolio_lesson,
    seed_agent_portfolio_memory,
)


def test_compact_and_format_empty_desk():
    raw = {
        "cash_pln": 1_000_000.0,
        "total_equity_pln": 1_000_000.0,
        "positions_value_pln": 0.0,
        "total_pnl_pln": 0.0,
        "total_pnl_pct": 0.0,
        "positions_count": 0,
        "positions": [],
        "recent_trades": [],
        "initial_cash_pln": 1_000_000.0,
    }
    summary = compact_portfolio_summary(raw)
    assert summary["cash_pln"] == 1_000_000.0
    assert summary["positions_count"] == 0
    lesson = format_portfolio_lesson(summary)
    assert "1000000" in lesson.replace(" ", "").replace(",", "") or "1 000 000" in lesson or "cash=1000000" in lesson
    assert "brak otwartych pozycji" in lesson


@pytest.mark.asyncio
async def test_seed_agent_portfolio_memory_upserts():
    portfolio = {
        "cash_pln": 1_000_000.0,
        "total_equity_pln": 1_000_000.0,
        "positions_value_pln": 0.0,
        "total_pnl_pln": 0.0,
        "total_pnl_pct": 0.0,
        "positions_count": 0,
        "positions": [],
        "recent_trades": [],
        "initial_cash_pln": 1_000_000.0,
    }
    upsert = AsyncMock()
    with patch("app.ai.db.upsert_learning_note", upsert):
        summary = await seed_agent_portfolio_memory(portfolio)
    assert summary["cash_pln"] == 1_000_000.0
    upsert.assert_awaited_once()
    kwargs = upsert.await_args.kwargs
    assert kwargs["topic"] == PORTFOLIO_MEMORY_TOPIC
    assert kwargs["source"] == PORTFOLIO_MEMORY_SOURCE
    assert "portfolio.db" in kwargs["lesson"]
