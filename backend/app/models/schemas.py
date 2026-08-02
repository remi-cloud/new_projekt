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


class AlphaModelStatus(BaseModel):
    """Public status for Model Alpha (crypto scoring layer)."""

    reference_date: date
    reference_price: float
    current_price: float
    days_since_reference: int
    phase_a_end_day: int = 364
    phase_b_end_day: int = 1428
    phase: CyclePhase
    phase_progress_pct: float
    days_remaining_in_phase: int
    signal: SignalAction
    rationale: str


class BetaPhase(str, Enum):
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    PHASE_4 = "phase_4"


class BetaModelStatus(BaseModel):
    """Public status for Model Beta (traditional markets scoring layer)."""

    period_start: date
    period_end: date
    current_phase: BetaPhase
    phase_number: int
    days_into_phase: int
    days_remaining_in_phase: int
    phase_progress_pct: float
    historical_bias: str
    signal: SignalAction
    rationale: str


# Internal aliases kept for gradual migration in engine modules
BitcoinCycleStatus = AlphaModelStatus
PresidentialCycleStatus = BetaModelStatus
PresidentialYear = BetaPhase


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
    alpha_model: AlphaModelStatus
    beta_model: BetaModelStatus
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


class WatchlistItem(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    source: str = "yahoo"
    enabled: bool = True
    created_at: Optional[str] = None


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    name: Optional[str] = None
    asset_class: Optional[AssetClass] = None


class WatchlistToggleRequest(BaseModel):
    enabled: bool


class AlertSettings(BaseModel):
    enabled: bool = False
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = ""
    webhook_url: str = ""
    min_confidence: float = Field(default=50, ge=0, le=100)
    actions: list[str] = Field(default_factory=lambda: ["buy", "sell"])
    alert_on_first_seen: bool = False


class AlertLogEntry(BaseModel):
    id: int
    channel: str
    status: str
    message: str
    detail: Optional[str] = None
    created_at: str


class TradeLevels(BaseModel):
    side: str
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward: float
    note: str


class HeatmapBin(BaseModel):
    price: float
    long_intensity: float
    short_intensity: float
    dominant: str
    intensity: float


class LiquidationHeatmap(BaseModel):
    price: float
    range_low: float
    range_high: float
    bins: list[HeatmapBin]
    columns: list[list[HeatmapBin]] = Field(default_factory=list)
    max_intensity: float = 1.0


class LiqPathPoint(BaseModel):
    t: float
    price: float
    role: str
    intensity: float = 0


class LiqAnchor(BaseModel):
    price: float
    role: str
    label: str
    t: float
    liq_side: Optional[str] = None


class LiqPrediction(BaseModel):
    direction: str
    confidence: float
    summary: str
    target_price: float
    target_side: str
    target_intensity: float = 0
    pull_up: float = 0
    pull_down: float = 0
    momentum: float = 0
    path: list[LiqPathPoint] = Field(default_factory=list)
    anchors: list[LiqAnchor] = Field(default_factory=list)
    features: dict = Field(default_factory=dict)


class SuperOpportunity(BaseModel):
    symbol: str
    name: str
    asset_class: str
    action: str
    cycle_confidence: float
    super_score: float
    is_super: bool
    cycle_source: str
    phase: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread_pct: Optional[float] = None
    book_source: Optional[str] = None
    levels: TradeLevels
    heatmap: LiquidationHeatmap
    prediction: Optional[LiqPrediction] = None
    reasons: list[str]
    rationale: str
    updated_at: str


class SuperOpportunitiesResponse(BaseModel):
    generated_at: str
    count: int
    super_count: int
    items: list[SuperOpportunity]
    supers: list[SuperOpportunity]
    scanner_last_scan_at: Optional[str] = None
