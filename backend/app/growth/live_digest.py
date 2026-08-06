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
    pres = scanner.presidential_cycle
    opps = sorted(
        scanner.opportunities,
        key=lambda o: (o.is_momentum_pick, o.confidence),
        reverse=True,
    )[:5]

    news_feed = await get_macro_news(category="all", limit=16, locale=locale)
    digest_news = sort_by_alignment(list(news_feed.items))[:6]
    watch = await top_watchlist(10)
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
        "bitcoin_cycle": btc.model_dump() if btc else None,
        "presidential_cycle": {
            "president": getattr(pres, "president", None),
            "current_year": (
                getattr(pres, "current_year", None).value
                if getattr(pres, "current_year", None) is not None
                and hasattr(getattr(pres, "current_year", None), "value")
                else str(getattr(pres, "current_year", "") or "")
            ),
            "year_number": getattr(pres, "year_number", None),
            "signal": (
                getattr(pres, "signal", None).value
                if getattr(pres, "signal", None) is not None and hasattr(getattr(pres, "signal", None), "value")
                else None
            ),
            "rationale": getattr(pres, "rationale", None),
            "current_year_expected_return_pct": getattr(pres, "current_year_expected_return_pct", None),
        }
        if pres
        else None,
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
            "newsletter": True,
        },
        "disclaimer": (
            "Sekcja informacyjna — nie stanowi rekomendacji inwestycyjnej. "
            "Cykle i projekcje opierają się na modelach heurystycznych i danych historycznych."
        ),
    }
