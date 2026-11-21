"""Public live digest for SEO / viral landing."""

from __future__ import annotations

from datetime import datetime, timezone

from app.growth import top_watchlist
from app.news.ideology_lens import sort_by_alignment
from app.news.macro_news import get_macro_news
from app.scanners.opportunity_scanner import scanner


async def build_live_digest(locale: str = "pl") -> dict:
    now = datetime.now(timezone.utc)
    btc = scanner.bitcoin_cycle
    opps = sorted(
        scanner.opportunities,
        key=lambda o: (o.is_momentum_pick, o.confidence),
        reverse=True,
    )[:5]

    news_feed = await get_macro_news(category="all", limit=16, locale=locale)
    digest_news = sort_by_alignment(list(news_feed.items))[:6]
    watch = await top_watchlist(10)
    # Votable candidates = real voted tickers + the scanner's current top picks
    # (with their real vote count, 0 if nobody voted yet). Nothing seeded.
    seen = {w["symbol"] for w in watch}
    for o in opps:
        if o.symbol not in seen and len(watch) < 10:
            watch.append({"symbol": o.symbol, "name": o.name, "votes": 0, "updated_at": None})
            seen.add(o.symbol)
    from app.data.community_links import resolve_community_links

    watch = [
        {
            **w,
            "community": resolve_community_links(w.get("symbol", ""), w.get("name")),
        }
        for w in watch
    ]

    return {
        "fetched_at": now.isoformat(),
        "status": "live" if scanner.live_mode else "online",
        "last_scan_at": scanner.last_scan_at.isoformat() if scanner.last_scan_at else None,
        "last_price_tick_at": (
            scanner.last_price_tick_at.isoformat() if scanner.last_price_tick_at else None
        ),
        "bitcoin_cycle": btc.model_dump() if btc else None,
        "top_opportunities": [
            {
                "symbol": o.symbol,
                "name": o.name,
                "action": o.action.value if hasattr(o.action, "value") else o.action,
                "confidence": o.confidence,
                "phase": o.phase,
                "price": o.price,
                "rationale": o.rationale[:160],
            }
            for o in opps
        ],
        "news": [
            {
                "id": n.id,
                "title": n.title,
                "source": n.source,
                "category": n.category,
                "url": n.url,
                "age_minutes": n.age_minutes,
                "image_url": n.image_url,
                "is_curated": n.is_curated,
            }
            for n in digest_news
        ],
        "watchlist": watch,
        "cta": {
            "calculator": "/kalkulator",
            "business": "/biznes",
        },
        "disclaimer": (
            "Sekcja informacyjna — nie stanowi rekomendacji inwestycyjnej. "
            "Cykle i projekcje opierają się na modelach heurystycznych i danych historycznych."
        ),
    }
