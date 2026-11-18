"""Guest POSTs that stay open without the desk token."""

PUBLIC_WRITE_PATHS = frozenset(
    {
        "/api/roi/calculate",
        "/api/growth/newsletter",
        "/api/growth/contact",
        "/api/growth/watchlist/vote",
        "/api/ai/chat",
    }
)
