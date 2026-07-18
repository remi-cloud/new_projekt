import pytest

from app.db import database as db
from app.db import settings_store as store
from app.notifications.dispatcher import format_change_message


@pytest.mark.asyncio
async def test_watchlist_seed_and_add(tmp_path, monkeypatch):
    db_path = tmp_path / "wl.db"
    monkeypatch.setattr(db.settings, "database_path", str(db_path))
    monkeypatch.setattr(store.settings, "database_path", str(db_path))
    await db.init_db()

    items = await store.get_watchlist()
    assert len(items) >= 20

    added = await store.add_watchlist_item("TSLA", "Tesla", "stock")
    assert added["symbol"] == "TSLA"
    assert added["name"] == "Tesla"

    removed = await store.remove_watchlist_item("TSLA")
    assert removed is True


@pytest.mark.asyncio
async def test_alert_settings_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "alerts.db"
    monkeypatch.setattr(db.settings, "database_path", str(db_path))
    monkeypatch.setattr(store.settings, "database_path", str(db_path))
    await db.init_db()

    saved = await store.save_alert_settings(
        {
            "enabled": True,
            "ntfy_server": "https://ntfy.sh",
            "ntfy_topic": "cyclical-test",
            "webhook_url": "",
            "min_confidence": 60,
            "actions": ["buy", "sell"],
            "alert_on_first_seen": False,
        }
    )
    assert saved["enabled"] is True
    assert saved["ntfy_topic"] == "cyclical-test"
    assert saved["min_confidence"] == 60


def test_format_change_message():
    msg = format_change_message(
        {
            "name": "Apple",
            "symbol": "AAPL",
            "previous_action": "watch",
            "new_action": "buy",
            "new_confidence": 72,
            "price": 190.5,
        }
    )
    assert "AAPL" in msg
    assert "KUPUJ" in msg
