from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.deps import ASSET_MAP
from app.cycles.signal_history import compute_cycle_markers
from app.data.broker_map import resolve_broker_info
from app.data.chart_data import CHART_PRESETS, fetch_chart
from app.models.schemas import AssetClass, AssetCycleAssessment, ChartResponse, SignalAction
from app.paper.pricing import PaperTradeError, get_live_price_async
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["markets"])


def _with_broker(item: AssetCycleAssessment) -> AssetCycleAssessment:
    info = resolve_broker_info(
        item.symbol,
        item.asset_class.value if hasattr(item.asset_class, "value") else str(item.asset_class),
        item.region,
    )
    return item.model_copy(update={"broker_info": info})


@router.get("/api/markets/assessments")
async def market_assessments(
    region: str | None = None,
    asset_class: str | None = None,
    signal: str | None = None,
):
    if not scanner.market_assessments:
        await scanner.scan()
    results = scanner.market_assessments
    if region:
        results = [a for a in results if a.region == region]
    if asset_class:
        results = [a for a in results if a.asset_class.value == asset_class]
    if signal:
        results = [a for a in results if a.signal.value == signal]
    return [_with_broker(a) for a in results]


@router.get("/api/markets/assessment/{symbol:path}", response_model=AssetCycleAssessment)
async def market_assessment(symbol: str):
    """Full cycle assessment or price-only fallback for known symbols."""
    if not scanner.market_assessments:
        await scanner.scan()
    item = next((a for a in scanner.market_assessments if a.symbol == symbol), None)
    if item:
        return _with_broker(item)

    meta = ASSET_MAP.get(symbol)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Nieznany instrument: {symbol}")

    try:
        price, _currency = await get_live_price_async(symbol)
    except PaperTradeError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc

    q = next((x for x in scanner.quotes if x.symbol == symbol), None)
    now = datetime.now(timezone.utc)
    asset_cls = meta.get("asset_class", "stock")
    try:
        parsed_class = AssetClass(asset_cls)
    except ValueError:
        parsed_class = AssetClass.STOCK

    return _with_broker(
        AssetCycleAssessment(
            symbol=symbol,
            name=meta.get("name", symbol),
            asset_class=parsed_class,
            region=meta.get("region", "global"),
            price=price,
            change_pct_24h=q.change_pct_24h if q else None,
            change_pct_7d=q.change_pct_7d if q else None,
            high_52w=None,
            drawdown_from_high_pct=None,
            macro_cycle="neutral",
            macro_phase="neutral",
            price_phase="neutral",
            momentum_score=None,
            momentum_signal=None,
            momentum_phase=None,
            is_momentum_pick=False,
            signal=SignalAction.WATCH,
            confidence=0,
            rationale="[Cena] Instrument poza ostatnim skanem — wyświetlamy dane cenowe i wykres.",
            updated_at=now,
        )
    )


@router.get("/api/markets/chart/{symbol:path}", response_model=ChartResponse)
async def market_chart(symbol: str, range: str = "3M"):
    if range not in CHART_PRESETS:
        range = "3M"
    chart = await fetch_chart(symbol, range)
    if not chart:
        raise HTTPException(status_code=404, detail=f"Brak danych wykresu dla {symbol}")

    meta = ASSET_MAP.get(symbol, {})
    btc = scanner.bitcoin_cycle
    markers = compute_cycle_markers(
        chart.candles,
        preset=range,
        asset_class=meta.get("asset_class", "stock"),
        region=meta.get("region", "global"),
        symbol=symbol,
        btc_ath_date=btc.last_ath_date if btc else None,
        btc_ath_price=btc.last_ath_price if btc else None,
    )
    return chart.model_copy(update={"cycle_markers": markers})


@router.get("/api/markets/quote/{symbol:path}")
async def market_quote(symbol: str):
    """Fresh live price (Yahoo v7 quote) — bypasses chart candle cache."""
    if symbol not in ASSET_MAP:
        raise HTTPException(status_code=404, detail=f"Nieznany instrument: {symbol}")
    try:
        price, currency = await get_live_price_async(symbol)
    except PaperTradeError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    q = next((x for x in scanner.quotes if x.symbol == symbol), None)
    return {
        "symbol": symbol,
        "price": price,
        "currency": currency,
        "change_pct_24h": q.change_pct_24h if q else None,
        "updated_at": q.updated_at.isoformat() if q and q.updated_at else None,
    }


@router.get("/api/markets/chart-presets")
async def chart_presets():
    return list(CHART_PRESETS.keys())
