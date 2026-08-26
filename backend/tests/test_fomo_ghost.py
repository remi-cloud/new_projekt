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


def test_offline_seed_traders_and_bag():
    from app.fomo.offline import humanize_cope_error, is_cope_unreachable, seed_bag_events, seed_traders

    traders = seed_traders(30)
    assert len(traders) == 30
    assert traders[0]["handle"]
    handles = [t["handle"] for t in traders]
    bag = seed_bag_events(handles, now_ts=1_700_000_000, n=3)
    assert len(bag) == 3
    assert all(e["action"] == "buy" for e in bag)
    assert is_cope_unreachable('Cope POST /register HTTP 530: {"title":"Error 1033: Cloudflare Tunnel error"}')
    assert "offline" in humanize_cope_error("error code: 1033").lower() or "degraded" in humanize_cope_error(
        "error code: 1033"
    ).lower() or "tunnel" in humanize_cope_error("error code: 1033").lower()


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
