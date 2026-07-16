from fastapi import APIRouter, HTTPException

from app.models.schemas import BusinessLeadRequest, NewsletterRequest, WatchlistVoteRequest
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["growth"])


@router.get("/api/public/live")
async def public_live(lang: str | None = None):
    from app.growth.live_digest import build_live_digest

    return await build_live_digest(locale=lang or "pl")


@router.get("/api/growth/packages")
async def growth_packages():
    from app.growth import list_packages

    return list_packages()


@router.post("/api/growth/newsletter")
async def growth_newsletter(body: NewsletterRequest):
    from app.growth import subscribe_newsletter

    try:
        return await subscribe_newsletter(body.email, body.locale, body.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/growth/contact")
async def growth_contact(body: BusinessLeadRequest):
    from app.growth import create_lead

    try:
        return await create_lead(
            name=body.name,
            email=body.email,
            company=body.company,
            package=body.package,
            message=body.message,
            locale=body.locale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/growth/watchlist")
async def growth_watchlist(limit: int = 12):
    from app.growth import top_watchlist

    return await top_watchlist(min(limit, 30))


@router.post("/api/growth/watchlist/vote")
async def growth_watchlist_vote(body: WatchlistVoteRequest):
    from app.growth import vote_watchlist

    try:
        return await vote_watchlist(body.symbol, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/embed/cycle")
async def embed_cycle():
    """JSON payload for third-party embeds / share cards."""
    btc = scanner.bitcoin_cycle
    if not btc:
        raise HTTPException(status_code=503, detail="Cycle data not ready — try again shortly")
    return {
        "brand": "kar digital · Cyclical Academy",
        "symbol": "BTC-USD",
        "phase": btc.phase.value,
        "signal": btc.signal.value,
        "days_since_ath": btc.days_since_ath,
        "ath_price": btc.last_ath_price,
        "ath_date": btc.last_ath_date.isoformat(),
        "current_price": btc.current_price,
        "progress_pct": btc.phase_progress_pct,
        "rationale": btc.rationale,
        "embed_url": "/embed",
        "live_url": "/live",
        "disclaimer": "Informational only — not investment advice.",
    }
