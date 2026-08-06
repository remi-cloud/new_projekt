"""Global cycle order book API + helpers."""

from __future__ import annotations

from app.cycles.global_cycle_book import get_global_cycle_book


def test_get_global_cycle_book_shape():
    data = get_global_cycle_book("all")
    assert "order_book" in data
    assert "profiles" in data
    assert "meta" in data
    assert "adopted" in data
    assert isinstance(data["order_book"], list)


def test_get_global_cycle_book_status_filter():
    all_book = get_global_cycle_book("all")["order_book"]
    adopted = get_global_cycle_book("adopted")["order_book"]
    assert all(e.get("status") == "adopted" for e in adopted)
    assert len(adopted) <= len(all_book)
