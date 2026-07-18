from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    STOCK = "stock"
    INDEX = "index"
    BOND = "bond"
    COMMODITY = "commodity"
    FOREX = "forex"


class SignalAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"


class CyclePhase(str, Enum):
    BEAR = "bear"
    ACCUMULATION = "accumulation"
    BULL = "bull"
    DISTRIBUTION = "distribution"
    NEUTRAL = "neutral"


class BitcoinCycleStatus(BaseModel):
    last_ath_date: date
    last_ath_price: float
    current_price: float
    days_since_ath: int
    bear_phase_end_day: int = 364
    bull_phase_end_day: int = 1428
    phase: CyclePhase
    phase_progress_pct: float
    days_remaining_in_phase: int
    signal: SignalAction
    rationale: str


class PresidentialYear(str, Enum):
    YEAR_1 = "year_1"
    YEAR_2 = "year_2"
    YEAR_3 = "year_3"
    YEAR_4 = "year_4"


class PresidentialCycleStatus(BaseModel):
    term_start: date
    term_end: date
    president: str
    current_year: PresidentialYear
    year_number: int
    days_into_year: int
    days_remaining_in_year: int
    year_progress_pct: float
    historical_bias: str
    signal: SignalAction
    rationale: str


class AssetQuote(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    price: float
    change_pct_24h: Optional[float] = None
    change_pct_7d: Optional[float] = None
    currency: str = "USD"
    updated_at: datetime


class Opportunity(BaseModel):
    id: Optional[int] = None
    symbol: str
    name: str
    asset_class: AssetClass
    action: SignalAction
    confidence: float = Field(ge=0, le=100)
    cycle_source: str
    phase: str
    price: float
    rationale: str
    created_at: datetime


class DashboardResponse(BaseModel):
    bitcoin_cycle: BitcoinCycleStatus
    presidential_cycle: PresidentialCycleStatus
    opportunities: list[Opportunity]
    monitored_assets: list[AssetQuote]
    last_scan_at: Optional[datetime] = None
    scanner_running: bool


class ScanLogEntry(BaseModel):
    id: int
    scanned_at: str
    opportunities_count: int
    changes_count: int = 0


class SignalChange(BaseModel):
    id: int
    scan_id: int
    symbol: str
    name: str
    asset_class: str
    previous_action: Optional[str] = None
    new_action: str
    previous_confidence: Optional[float] = None
    new_confidence: float
    cycle_source: str
    phase: str
    price: float
    created_at: str


class HistoryResponse(BaseModel):
    scans: list[ScanLogEntry]
    changes: list[SignalChange]
    recent_opportunities: list[dict]
