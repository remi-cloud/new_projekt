"""Guest POSTs that stay open without the desk token."""

PUBLIC_WRITE_PATHS = frozenset(
    {
        "/api/roi/calculate",
        "/api/growth/newsletter",
        "/api/growth/contact",
        "/api/growth/watchlist/vote",
        "/api/ai/chat",
        # /api/ai/analyze/{symbol} stays off this list. It is a heavier desk write.
        # Guests use chat. The agent page disables Pełna analiza until the desk session is open.
    }
)
