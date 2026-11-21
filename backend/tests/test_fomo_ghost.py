import pytest
"""FOMO Ghost — filter + normalize (no network)."""

from app.fomo.client import normalize_activity, normalize_trader
from app.fomo.service import filter_activity_to_top


def test_normalize_trader_handle():
    t = normalize_trader({"handle": "@alpha", "pnl": 12000, "win_rate": 72.5, "trades": 40}, rank=1)
    assert t["handle"] == "alpha"
    assert t["rank"] == 1
    assert t["pnl"] == 12000


def test_normalize_activity_buy():
    ev = normalize_activity(
        {
            "handle": "whale1",
            "action": "buy",
            "mint": "So11111111111111111111111111111111111111112",
            "symbol": "SOL",
            "chain": "solana",
            "usd_amount": 2500,
            "timestamp": 1700000000,
        }
    )
    assert ev is not None
    assert ev["action"] == "buy"
    assert ev["symbol"] == "SOL"
    assert ev["ts_unix"] == 1700000000


def test_filter_activity_to_top_only():
    handles = {"alpha", "beta"}
    rows = [
        {"handle": "alpha", "action": "buy", "mint": "m1", "symbol": "AAA", "usd_amount": 100, "ts": 1},
        {"handle": "gamma", "action": "buy", "mint": "m2", "symbol": "BBB", "usd_amount": 200, "ts": 2},
        {"handle": "beta", "action": "sell", "mint": "m3", "symbol": "CCC", "usd_amount": 50, "ts": 3},
    ]
    out = filter_activity_to_top(rows, handles)
    assert len(out) == 2
    assert {e["handle"] for e in out} == {"alpha", "beta"}
    assert {e["action"] for e in out} == {"buy", "sell"}


def test_resolve_key_empty(monkeypatch):
    from app.config import settings
    from app.fomo.client import resolve_cope_api_key
    from app.fomo import service as fomo_service

    monkeypatch.setattr(settings, "cope_api_key", "")
    monkeypatch.delenv("COPE_API_KEY", raising=False)
    monkeypatch.setattr(fomo_service, "load_persisted_key", lambda: "")
    assert resolve_cope_api_key() == ""
    assert fomo_service.effective_api_key() == ""


def test_offline_helpers_invent_no_traders():
    import app.fomo.offline as offline
    from app.fomo.offline import humanize_cope_error, is_cope_unreachable

    assert not hasattr(offline, "seed_traders")
    assert not hasattr(offline, "seed_bag_events")
    assert is_cope_unreachable('Cope POST /register HTTP 530: {"title":"Error 1033: Cloudflare Tunnel error"}')
    assert "brak danych" in humanize_cope_error("error code: 1033").lower()


@pytest.mark.asyncio
async def test_degraded_tick_inserts_nothing_and_purges_old_fakes(tmp_path, monkeypatch):
    from app.fomo import db as fomo_db
    from app.fomo import service as fomo_service

    await fomo_db.init_fomo_db()
    await fomo_db.replace_top_traders(
        [{"rank": 1, "handle": "fake_seed", "pnl": 1.0, "win_rate": 50.0, "trades": 1, "raw": {"source": "offline_seed"}}]
    )
    out = await fomo_service.run_degraded_tick(reason="error code: 1033")
    assert out["inserted"] == 0 and out["new_buys"] == []
    handles = [t["handle"] for t in await fomo_db.list_top_traders(50)]
    assert "fake_seed" not in handles


def test_normalize_fomo_handle_field():
    ev = normalize_activity(
        {
            "fomo_handle": "frankdegods",
            "action": "buy",
            "token_mint": "DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump",
            "token_symbol": "BONK",
            "chain": "solana",
            "usd_amount": 2400.5,
            "timestamp": 1707603400,
        }
    )
    assert ev is not None
    assert ev["handle"] == "frankdegods"
    assert ev["symbol"] == "BONK"
