from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.ai.pearl_hunter.db import get_find_by_symbol
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


def _parse_asset_class(raw: str | None) -> AssetClass:
    try:
        return AssetClass(raw or "stock")
    except ValueError:
        return AssetClass.STOCK


def _price_only_assessment(
    symbol: str,
    *,
    name: str,
    asset_class: str,
    region: str,
    price: float,
    change_pct_24h: float | None,
    change_pct_7d: float | None,
    rationale: str,
) -> AssetCycleAssessment:
    return AssetCycleAssessment(
        symbol=symbol,
        name=name,
        asset_class=_parse_asset_class(asset_class),
        region=region or "global",
        price=price,
        change_pct_24h=change_pct_24h,
        change_pct_7d=change_pct_7d,
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
        rationale=rationale,
        updated_at=datetime.now(timezone.utc),
    )


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
    """Full cycle assessment or price-only fallback (monitored + pearls + Yahoo)."""
    if not scanner.market_assessments:
        await scanner.scan()
    item = next((a for a in scanner.market_assessments if a.symbol == symbol), None)
    if item:
        return _with_broker(item)

    meta = ASSET_MAP.get(symbol)
    pearl = None if meta else await get_find_by_symbol(symbol)

    name = (meta or {}).get("name") or (pearl or {}).get("name") or symbol
    asset_cls = (meta or {}).get("asset_class") or (pearl or {}).get("asset_class") or "stock"
    region = (meta or {}).get("region") or (pearl or {}).get("region") or "global"

    price: float | None = None
    change_24h: float | None = None
    change_7d: float | None = None

    try:
        price, _currency = await get_live_price_async(symbol)
        q = next((x for x in scanner.quotes if x.symbol == symbol), None)
        change_24h = q.change_pct_24h if q else None
        change_7d = q.change_pct_7d if q else None
    except PaperTradeError:
        if pearl and pearl.get("price"):
            price = float(pearl["price"])
            change_24h = pearl.get("change_pct_24h")
        else:
            chart = await fetch_chart(symbol, "1D")
            if chart and chart.candles:
                price = float(chart.candles[-1].close)
                name = chart.name or name
            elif not meta and not pearl:
                raise HTTPException(status_code=404, detail=f"Nieznany instrument: {symbol}")
            else:
                raise HTTPException(status_code=404, detail=f"Brak ceny dla {symbol}")

    if price is None:
        raise HTTPException(status_code=404, detail=f"Brak ceny dla {symbol}")

    if pearl and not meta:
        rationale = (
            f"[Perełka] {pearl.get('rationale') or 'Instrument z łowców pereł — wykres i cena na żywo.'}"
        )
    elif meta:
        rationale = "[Cena] Instrument poza ostatnim skanem — wyświetlamy dane cenowe i wykres."
    else:
        rationale = "[Cena] Instrument spoza listy monitorowanej — wykres Yahoo / cena."

    pearl_chg = (pearl or {}).get("change_pct_24h")
    return _with_broker(
        _price_only_assessment(
            symbol,
            name=name,
            asset_class=str(asset_cls),
            region=str(region),
            price=price,
            change_pct_24h=change_24h if change_24h is not None else pearl_chg,
            change_pct_7d=change_7d,
            rationale=rationale,
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
    if not meta:
        pearl = await get_find_by_symbol(symbol)
        if pearl:
            meta = {
                "asset_class": pearl.get("asset_class", "stock"),
                "region": pearl.get("region", "global"),
            }
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
    known = symbol in ASSET_MAP
    pearl = None if known else await get_find_by_symbol(symbol)
    try:
        price, currency = await get_live_price_async(symbol)
    except PaperTradeError as exc:
        if pearl and pearl.get("price"):
            return {
                "symbol": symbol,
                "price": float(pearl["price"]),
                "currency": "USD",
                "change_pct_24h": pearl.get("change_pct_24h"),
                "updated_at": pearl.get("found_at"),
            }
        if not known and not pearl:
            raise HTTPException(status_code=404, detail=f"Nieznany instrument: {symbol}") from exc
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
