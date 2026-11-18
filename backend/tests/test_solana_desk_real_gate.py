"""Real mode stays locked. The wallet key never leaves the process."""

import logging
import os
from pathlib import Path

from app.solana_desk.real_gate import (
    KEY,
    JupiterSwapGateway,
    RealTradingLocked,
    real_mode_view,
    solscan_tx_url,
)

ROOT = Path(__file__).resolve().parents[2]
SECRET = "paper-only-secret-value-not-a-key"


def test_default_is_paper_even_with_a_key(monkeypatch):
    monkeypatch.delenv("SOLANA_REAL_TRADING", raising=False)
    monkeypatch.setenv(KEY, SECRET)
    view = real_mode_view()
    assert view["mode"] == "paper"
    assert view["real_trading_active"] is False
    assert view["wallet_configured"] is True
    assert SECRET not in str(view)


def test_flag_without_a_key_stays_locked(monkeypatch):
    monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
    monkeypatch.delenv(KEY, raising=False)
    view = real_mode_view()
    assert view["real_trading_active"] is False
    assert "SOLANA_BOT_PRIVATE_KEY" in view["lock_reason"]
    gateway = JupiterSwapGateway()
    intent = gateway.build_intent(mint="Mintpump", side="buy", amount_sol=0.05)
    assert intent["broadcast"] is False
    assert SECRET not in str(intent)
    with pytest_raises():
        gateway.execute(intent)


def pytest_raises():
    import pytest

    return pytest.raises(RealTradingLocked)


def test_flag_and_key_still_do_not_broadcast(monkeypatch):
    monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
    monkeypatch.setenv(KEY, SECRET)
    view = real_mode_view()
    blob = str(view)
    assert SECRET not in blob
    assert view["real_trading_active"] is False
    assert view["armed"] is False
    assert "SOLANA_RPC_URL" in view["lock_reason"]
    with pytest_raises():
        JupiterSwapGateway().execute({"mint": "Mintpump"})


def test_child_logger_and_traceback_drop_the_wallet_secret(monkeypatch):
    monkeypatch.setenv(KEY, SECRET)
    logger = logging.getLogger("app.solana_desk.live")
    lines: list[str] = []

    class _Grab(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(logging.Formatter().format(record))

    handler = _Grab(level=logging.ERROR)
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    try:
        logger.error("portfel %s", SECRET)
        try:
            raise RuntimeError(f"podpis {SECRET}")
        except RuntimeError:
            logger.exception("awaria podpisu")
    finally:
        logger.removeHandler(handler)
    assert lines
    assert all(SECRET not in line for line in lines)
    assert any("[redacted]" in line for line in lines)


def test_log_line_is_scrubbed(monkeypatch):
    monkeypatch.setenv(KEY, SECRET)
    logger = logging.getLogger("app.solana_desk")
    records = []

    class _Grab(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = _Grab()
    logger.addHandler(handler)
    try:
        logger.info("próba %s", SECRET)
        logger.info("w treści %s koniec", f"klucz {SECRET}")
    finally:
        logger.removeHandler(handler)
    assert records
    assert all(SECRET not in line for line in records)


def test_solscan_link_only_for_a_real_signature():
    assert solscan_tx_url(None) is None
    assert solscan_tx_url("") is None
    assert solscan_tx_url("not a sig") is None
    url = solscan_tx_url("5" * 64)
    assert url == "https://solscan.io/tx/" + "5" * 64


def test_worker_process_configures_logging(monkeypatch):
    import logging

    from app.solana_desk import worker

    ran = {}

    def fake_run(coro):
        ran["ok"] = True
        coro.close()

    monkeypatch.setattr(worker.asyncio, "run", fake_run)
    root = logging.getLogger()
    previous_handlers = list(root.handlers)
    previous_level = root.level
    root.handlers.clear()
    try:
        worker.main()
        assert ran.get("ok") is True
        assert root.level == logging.INFO
        assert root.handlers
    finally:
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)


def test_compose_worker_defaults_to_paper_and_has_no_key():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "solana-desk:" in text
    assert "app.solana_desk.worker" in text
    assert '${SOLANA_REAL_TRADING:-false}' in text
    assert "SOLANA_BOT_PRIVATE_KEY:" not in text
    assert SECRET not in text
