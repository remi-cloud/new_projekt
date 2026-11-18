"""Regression checks for the interactive-audit hardening pass."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.desk_auth import reset_login_guard
from app.http_guard import _HITS
from app.news.google_news_urls import decoder_from_module
from app.news.macro_news import RSS_SOURCES
from app.news.public_urls import live_domain_ready
from app.news.x_auto import evaluate_auto


def test_settings_read_desk_token_from_env_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CYCLICAL_DESK_TOKEN", raising=False)
    env = tmp_path / ".env"
    env.write_text("CYCLICAL_DESK_TOKEN=z-pliku\n", encoding="utf-8")
    loaded = Settings(_env_file=env)
    assert loaded.desk_token == "z-pliku"


def test_auto_post_is_on_by_default_and_waits_without_a_domain(monkeypatch):
    monkeypatch.setattr(settings, "public_base_url", "")
    assert Settings.model_fields["social_auto_post"].default is True
    assert live_domain_ready() is False
    monkeypatch.setattr(settings, "public_base_url", "https://kardigital.example")
    assert live_domain_ready() is True
    monkeypatch.setattr(settings, "public_base_url", "https://example.trycloudflare.com")
    assert live_domain_ready() is False


def test_shell_loader_exports_desk_token(tmp_path: Path):
    import os
    import subprocess

    env_file = tmp_path / ".env"
    env_file.write_text('CYCLICAL_DESK_TOKEN="z-skryptu"\n', encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "scripts" / "load-dotenv.sh"
    result = subprocess.run(
        ["bash", "-c", f'source "{script}" && load_dotenv "{env_file}" && printf %s "$CYCLICAL_DESK_TOKEN"'],
        check=True,
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if key != "CYCLICAL_DESK_TOKEN"},
    )
    assert result.stdout == "z-skryptu"


def test_guest_calculator_is_not_blocked_by_the_desk(client: TestClient):
    _HITS.clear()
    response = client.post(
        "/api/roi/calculate",
        headers={"X-Desk-Token": ""},
        json={"symbol": "BTC-USD", "amount": 1000, "strategy": "buy_hold", "years": 1},
    )
    assert response.status_code != 401
    assert response.status_code != 403


def test_foreign_origin_cannot_post_the_public_form(client: TestClient):
    _HITS.clear()
    response = client.post(
        "/api/growth/newsletter",
        headers={"X-Desk-Token": "", "Origin": "https://evil.example"},
        json={"email": "a@b.co", "locale": "pl"},
    )
    assert response.status_code == 403


def test_login_locks_after_five_failures(client: TestClient, monkeypatch):
    reset_login_guard()
    _HITS.clear()
    monkeypatch.setattr(settings, "desk_token", "prawidlowy-token")
    codes = [
        client.post("/api/desk/login", json={"token": "zly"}).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [401, 401, 401, 401, 401]
    assert codes[5] == 429
    reset_login_guard()
    _HITS.clear()


def test_notification_phone_is_hidden_without_the_desk(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "desk_token", "pytest-desk")
    saved = client.put(
        "/api/notifications/settings",
        json={"phone": "+48111222333", "sms_enabled": False, "ntfy_enabled": False, "ntfy_topic": "sekret-temat"},
    )
    assert saved.status_code == 200
    hidden = client.get("/api/notifications/status", headers={"X-Desk-Token": ""})
    body = hidden.json()
    assert "111222333" not in hidden.text
    assert "sekret-temat" not in hidden.text
    assert body["settings"]["phone"].startswith("•••")


def test_notification_log_limit_is_clamped(client: TestClient):
    response = client.get("/api/notifications/log", params={"limit": -1})
    assert response.status_code == 200
    assert len(response.json()) <= 100


def test_vapid_key_is_generated_without_py_vapid_internals():
    from app.notifications.vapid_setup import ensure_vapid_keys

    public, private = ensure_vapid_keys()
    assert public
    assert "BEGIN" in private or private


def test_sms_choice_survives_another_startup():
    import asyncio

    from app.db.database import get_alert_settings, init_db, update_alert_settings

    async def _run():
        await init_db()
        await update_alert_settings({"sms_enabled": False, "phone": "+48111222333"})
        await init_db()
        return await get_alert_settings()

    data = asyncio.run(_run())
    assert data["sms_enabled"] is False
    assert data["ntfy_enabled"] is False


def test_partial_alert_save_keeps_the_other_flags():
    import asyncio

    from app.db.database import get_alert_settings, init_db, update_alert_settings

    async def _run():
        await init_db()
        await update_alert_settings({"push_enabled": False, "sms_enabled": False, "alert_on_macro_news": False})
        await update_alert_settings({"phone": "+48000000000"})
        return await get_alert_settings()

    data = asyncio.run(_run())
    assert data["push_enabled"] is False
    assert data["alert_on_macro_news"] is False
    assert data["phone"].endswith("0000")


def test_decoder_accepts_the_function_this_install_exports():
    class Module:
        new_decoderv2 = staticmethod(lambda url: {"status": True, "decoded_url": "https://www.reuters.com/a"})

    assert callable(decoder_from_module(Module()))
    assert decoder_from_module(object()) is None


def test_retired_feeds_and_dead_symbols_are_gone():
    urls = " ".join(url for url, _name, _cat in RSS_SOURCES)
    for dead in ("finance.yahoo.com", "space.com", "foxbusiness.com", "euronews.com", "blockchain.com"):
        assert dead not in urls
    from app.data.regional_universe import REGIONAL_UNIVERSE
    from app.data.tokenized_universe import TOKENIZED_UNIVERSE

    symbols = {row["symbol"] for row in [*TOKENIZED_UNIVERSE, *REGIONAL_UNIVERSE]}
    assert "METAX-USD" not in symbols
    assert "GMEX-USD" not in symbols
    assert "GLDX-USD" not in symbols
    assert "WIG20LEV.WA" not in symbols


def test_external_llm_is_off_without_opt_in(monkeypatch):
    from app.ai.llm import _local_target, _targets_for_request

    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "ai_external_enabled", False)
    monkeypatch.setattr(settings, "ollama_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(settings, "ollama_model", "llama3.2")
    targets = _targets_for_request()
    assert targets
    assert all(_local_target(target) for target in targets)
    assert all(target.provider != "llm7" for target in targets)


def test_sqlite_backup_uses_the_backup_api(tmp_path, monkeypatch):
    from app.backup.progress_autosave import save_progress

    src = tmp_path / "trader.db"
    connection = sqlite3.connect(src)
    connection.execute("CREATE TABLE t (id INTEGER)")
    connection.execute("INSERT INTO t VALUES (1)")
    connection.commit()
    connection.close()
    monkeypatch.setattr("app.backup.progress_autosave.database_path", lambda: src)
    monkeypatch.setattr("app.backup.progress_autosave.portfolio_database_path", lambda: tmp_path / "missing.db")
    monkeypatch.setattr("app.backup.progress_autosave.PROGRESS_DIR", tmp_path / "progress")
    monkeypatch.setattr("app.backup.progress_autosave.SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr("app.backup.progress_autosave.REPO_ROOT", tmp_path)
    saved = save_progress(reason="test")
    assert "trader.db" in saved["copied"]
    assert "/data/" not in saved["progress_path"]
    copy = sqlite3.connect(tmp_path / "progress" / "current" / "trader.db")
    assert copy.execute("SELECT id FROM t").fetchone()[0] == 1
    copy.close()


def _item():
    from app.models.schemas import MacroNewsItem

    return MacroNewsItem(
        id="domain-gate-1",
        title="Fed holds rates as inflation stays sticky",
        summary="The Federal Reserve left interest rates unchanged.",
        url="https://www.reuters.com/markets/fed-holds",
        source="Reuters",
        category="fed",
        impact="high",
        published_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )


@pytest.mark.asyncio
async def test_auto_x_does_not_post_without_a_public_domain():
    from app.news.social_db import init_social_db, list_decisions
    from app.notifications import social_dispatcher as sd

    await init_social_db()
    with (
        patch.object(sd, "post_to_x", new_callable=AsyncMock) as post,
        patch.object(sd, "x_configured", return_value=True),
        patch.object(sd.settings, "social_auto_post", True),
        patch.object(sd.settings, "social_dry_run", False),
        patch.object(sd.settings, "public_base_url", ""),
        patch.object(sd.social_db, "count_posted_since", new_callable=AsyncMock, return_value=0),
    ):
        result = await sd.run_auto_x([_item()])
    assert result["published"] == 0
    post.assert_not_called()
    rows = await list_decisions(20)
    assert any(row["reason"] == "czeka na domenę" for row in rows)


def test_source_line_is_required_and_hourly_cap_blocks():
    from app.news.x_auto import assert_post_has_source

    blocked = evaluate_auto(
        source="Reuters",
        url="https://www.reuters.com/markets/fed-holds",
        title="Fed holds rates as inflation stays sticky",
        summary="The Federal Reserve left interest rates unchanged.",
        impact="high",
        category="fed",
        published_at=datetime(2026, 11, 17, 14, 40, tzinfo=timezone.utc),
        now=datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc),
        confirming_sources=2,
        posted_last_day=0,
        recent_topics=set(),
        min_score=70,
        max_per_day=2,
        posted_last_hour=2,
        max_per_hour=2,
    )
    assert blocked.action == "reject"
    assert "godzinę" in blocked.reason
    with pytest.raises(RuntimeError):
        assert_post_has_source("bez źródła", "Reuters", "https://www.reuters.com/a")


def test_queue_path_uses_the_same_domain_gate():
    import asyncio

    from app.notifications import social_dispatcher as sd

    async def _run():
        with (
            patch.object(sd.settings, "public_base_url", ""),
            patch.object(sd.settings, "social_auto_post", True),
        ):
            return await sd._queue_live_guard(_item(), "Źródło: Reuters\nhttps://www.reuters.com/a", "x")

    assert asyncio.run(_run()) == "czeka na domenę"
