"""Coordinator + Binance bridge tests (no network)."""

from datetime import datetime, timezone

from app.coordinator import service as coordinator_service
from app.coordinator.link_guard import audit_terminal_urls
from app.launch_scout.terminal_url import terminal_url


def test_link_guard_ok_for_chain_axiom():
    url = terminal_url(mint="DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump", chain="solana")
    audit = audit_terminal_urls([{"chain": "solana", "url": url}])
    assert audit["ok"] is True
    assert audit["missing_chain_axiom"] == 0


def test_link_guard_flags_missing_chain():
    audit = audit_terminal_urls(
        [{"chain": "solana", "url": "https://axiom.trade/meme/abc123"}]
    )
    assert audit["missing_chain_axiom"] == 1
    assert audit["ok"] is False


def test_desk_ok_warming_up_during_grace():
    coordinator_service.mark_app_started()
    assert coordinator_service._desk_ok(
        last_tick=None,
        interval_sec=60,
        last_error=None,
        in_grace=True,
    )


def test_desk_not_ok_stale_after_grace():
    assert not coordinator_service._desk_ok(
        last_tick=None,
        interval_sec=60,
        last_error=None,
        in_grace=False,
    )


def test_startup_grace_window():
    coordinator_service.mark_app_started()
    assert coordinator_service._in_startup_grace(90) is True
    coordinator_service._app_started_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert coordinator_service._in_startup_grace(90) is False
