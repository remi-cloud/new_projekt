"""max_open uses the real open book, not a hardcoded zero."""

from app.solana_desk.service import _open_count


def test_open_count_counts_pending_and_open_and_skips_the_fill():
    rows = [
        {"mint": "other", "status": "open"},
        {"mint": "mine", "status": "pending"},
        {"mint": "done", "status": "closed"},
    ]
    assert _open_count(rows, skip_mint="mine") == 1
    assert _open_count(rows) == 2
    assert _open_count([]) == 0
