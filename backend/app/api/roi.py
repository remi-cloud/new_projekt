import logging

from fastapi import APIRouter, HTTPException

from app.api.deps import ASSET_MAP
from app.models.schemas import RoiCalculateRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["roi"])


@router.get("/api/roi/assets")
async def roi_assets():
    from app.roi.calculator import list_roi_assets

    return list_roi_assets()


@router.get("/api/roi/showcase")
async def roi_showcase(years: int = 10, amount: float = 10000):
    from app.roi.showcase import get_showcase

    try:
        return await get_showcase(years=years, amount=amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ROI showcase failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not build ROI showcase") from exc


@router.get("/api/roi/program-us-1995")
async def program_us_1995(amount: float = 1000.0):
    """Backtest program cycle signals on ^GSPC from 1995 with $1000 vs buy&hold."""
    from app.roi.calculator import calculate_program_us_backtest

    try:
        return await calculate_program_us_backtest(amount=amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Program US 1995 backtest failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not run program backtest") from exc


@router.post("/api/roi/calculate")
async def roi_calculate(body: RoiCalculateRequest):
    from datetime import date as date_cls

    from app.roi.calculator import calculate_roi
    from app.roi.forward import project_forward

    if body.symbol not in ASSET_MAP:
        raise HTTPException(status_code=404, detail="Unknown symbol")
    if body.strategy not in ("buy_hold", "cycle", "dca", "cycle_dca"):
        raise HTTPException(status_code=400, detail="strategy: buy_hold, cycle, dca, cycle_dca")
    mode = (body.mode or "forward").lower()
    if mode not in ("forward", "backtest"):
        raise HTTPException(status_code=400, detail="mode: forward, backtest")
    try:
        if mode == "forward":
            return await project_forward(
                symbol=body.symbol,
                amount=body.amount,
                years=body.years,
                strategy=body.strategy,
                monthly_contribution=body.monthly_contribution,
            )
        start = body.start
        end = body.end
        if isinstance(start, str):
            start = date_cls.fromisoformat(start)
        if isinstance(end, str):
            end = date_cls.fromisoformat(end)
        result = await calculate_roi(
            symbol=body.symbol,
            amount=body.amount,
            strategy=body.strategy,  # type: ignore[arg-type]
            start=start,
            end=end,
            compare_buy_hold=body.compare_buy_hold,
        )
        result["mode"] = "backtest"
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ROI calculate failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not calculate ROI") from exc
