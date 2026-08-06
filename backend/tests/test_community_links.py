"""Unit tests for instrument community link resolver."""

from app.data.community_links import resolve_community_links


def test_btc_official_x():
    c = resolve_community_links("BTC-USD", "Bitcoin")
    assert c["x"] == "https://x.com/bitcoin"
    assert c["x_official"] is True
    assert c.get("website")


def test_aapl_and_tokenized_inherit():
    aapl = resolve_community_links("AAPL", "Apple")
    assert aapl["x_official"] is True
    ax = resolve_community_links("AAPLX-USD", "Apple xStock")
    assert ax["x"] == aapl["x"]
    assert ax["x_official"] is True


def test_unknown_symbol_x_search_fallback():
    c = resolve_community_links("ZZZZ-USD", "Mystery Coin")
    assert c["x_official"] is False
    assert "x.com/search" in c["x"]
    assert "ZZZZ" in c["x"]
