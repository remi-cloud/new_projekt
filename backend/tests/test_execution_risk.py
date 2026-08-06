"""Tests for execution risk checks."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.execution.models import SignalCandidate
from app.execution.risk import check_risk


def test_risk_disabled():
    c = SignalCandidate(symbol="AAPL", name="Apple", asset_class="stock", source="opportunity", confidence=90)
    ok, reason = asyncio.run(check_risk(c, enabled=False))
    assert not ok
    assert reason == "execution_disabled"


def test_risk_daily_limit():
    c = SignalCandidate(symbol="AAPL", name="Apple", asset_class="stock", source="opportunity", confidence=90)
    with patch("app.execution.risk.exec_db.count_proposals_today", new=AsyncMock(return_value=99)):
        with patch("app.execution.risk.exec_db.recent_symbol_proposal", new=AsyncMock(return_value=None)):
            with patch("app.execution.risk.paper_db.get_position", new=AsyncMock(return_value=None)):
                ok, reason = asyncio.run(check_risk(c, enabled=True, max_daily=5))
    assert not ok
    assert reason == "daily_limit_reached"


def test_risk_ok():
    c = SignalCandidate(symbol="AAPL", name="Apple", asset_class="stock", source="opportunity", confidence=90)
    with patch("app.execution.risk.exec_db.count_proposals_today", new=AsyncMock(return_value=0)):
        with patch("app.execution.risk.exec_db.recent_symbol_proposal", new=AsyncMock(return_value=None)):
            with patch("app.execution.risk.paper_db.get_position", new=AsyncMock(return_value=None)):
                ok, reason = asyncio.run(check_risk(c, enabled=True))
    assert ok
    assert reason == "ok"
