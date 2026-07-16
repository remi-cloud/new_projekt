from fastapi import APIRouter

from app.models.schemas import RegionalCycleSnapshot
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["cycles"])


@router.get("/api/cycles/bitcoin")
async def bitcoin_cycle():
    if not scanner.bitcoin_cycle:
        await scanner.scan()
    return scanner.bitcoin_cycle


@router.get("/api/cycles/presidential")
async def presidential_cycle():
    if not scanner.presidential_cycle:
        await scanner.scan()
    return scanner.presidential_cycle


@router.get("/api/cycles/regional", response_model=list[RegionalCycleSnapshot])
async def regional_cycles():
    if not scanner.regional_cycles:
        await scanner.scan()
    return scanner.regional_cycles
