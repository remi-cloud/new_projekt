import pytest

from app.db import database as db
from app.models.schemas import AssetClass, Opportunity, SignalAction
from datetime import datetime, timezone


def _opp(symbol: str, action: SignalAction, confidence: float = 70) -> Opportunity:
    return Opportunity(
        symbol=symbol,
        name=symbol,
        asset_class=AssetClass.STOCK,
        action=action,
        confidence=confidence,
        cycle_source="beta",
        phase="year_3",
        price=100.0,
        rationale="test",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_save_detects_signal_changes(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db.settings, "database_path", str(db_path))
    await db.init_db()

    first = await db.save_opportunities([_opp("AAPL", SignalAction.BUY)])
    assert first["opportunities_count"] == 1
    assert first["changes_count"] == 1  # first appearance counts as change

    second = await db.save_opportunities([_opp("AAPL", SignalAction.BUY, 72)])
    assert second["changes_count"] == 0  # same action

    third = await db.save_opportunities([_opp("AAPL", SignalAction.SELL)])
    assert third["changes_count"] == 1

    changes = await db.get_signal_changes()
    assert len(changes) == 2
    assert changes[0]["new_action"] == "sell"
    assert changes[0]["previous_action"] == "buy"
