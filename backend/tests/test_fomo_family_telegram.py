"""FOMO Family bags + Telegram parser (no network)."""

from app.fomo.bags import reconstruct_bags_from_events
from app.fomo.telegram_parser import looks_like_fomo_message, parse_fomo_telegram_message


def test_reconstruct_open_and_closed():
    events = [
        {
            "handle": "alpha",
            "action": "buy",
            "mint": "DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump",
            "symbol": "BONK",
            "chain": "solana",
            "usd_amount": 1000,
            "ts_unix": 100,
        },
        {
            "handle": "alpha",
            "action": "sell",
            "mint": "DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump",
            "symbol": "BONK",
            "chain": "solana",
            "usd_amount": 1000,
            "ts_unix": 200,
        },
        {
            "handle": "beta",
            "action": "buy",
            "mint": "So11111111111111111111111111111111111111112",
            "symbol": "SOL",
            "chain": "solana",
            "usd_amount": 500,
            "ts_unix": 150,
        },
    ]
    bags = reconstruct_bags_from_events(events, include_closed=True)
    by_h = {b["handle"]: b for b in bags}
    assert by_h["beta"]["status"] == "open"
    assert by_h["alpha"]["status"] == "closed"
    open_only = reconstruct_bags_from_events(events, include_closed=False)
    assert len(open_only) == 1
    assert open_only[0]["handle"] == "beta"


def test_parse_fomo_telegram_buy():
    text = (
        "@whale1 bought $PEPE for $12.5k "
        "DezX7iJ4W8VqRXPpWLNq6YYr5ky2nrSR1GvSa8L7pump fomo.family"
    )
    assert looks_like_fomo_message(text)
    sigs = parse_fomo_telegram_message(text)
    assert len(sigs) == 1
    assert sigs[0].action == "buy"
    assert sigs[0].handle == "whale1"
    assert sigs[0].symbol == "PEPE"
    assert sigs[0].usd_amount == 12500


def test_parse_dedicated_channel_needs_mint():
    mint = "So11111111111111111111111111111111111111112"
    sigs = parse_fomo_telegram_message(
        f"alert entry {mint}",
        default_handle="tg_channel",
        chat_id="-1001",
    )
    assert len(sigs) == 1
    assert sigs[0].mint == mint
