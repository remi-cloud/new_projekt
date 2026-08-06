"""Unit tests for Telegram Predator parser (no network)."""

from app.telegram.predator_parser import parse_predator_message


def test_parse_long_btc():
    out = parse_predator_message("🟢 LONG BTC/USDT entry now — Predator signal")
    assert out
    assert out[0].action == "buy"
    assert out[0].symbol == "BTC-USD"


def test_parse_short_eth():
    out = parse_predator_message("SHORT #ETH leverage 5x")
    assert out
    assert out[0].action == "sell"
    assert out[0].symbol == "ETH-USD"


def test_parse_buy_pepe():
    out = parse_predator_message("BUY PEPEUSDT strong momentum")
    assert out
    assert out[0].action == "buy"
    assert out[0].symbol == "PEPE-USD"


def test_parse_empty():
    assert parse_predator_message("") == []
    assert parse_predator_message("hello world no signal") == []
