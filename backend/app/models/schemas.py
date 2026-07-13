from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    STOCK = "stock"
    ETF = "etf"
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


class AssetCycleAssessment(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    region: str
    price: float
    change_pct_24h: Optional[float] = None
    change_pct_7d: Optional[float] = None
    high_52w: Optional[float] = None
    drawdown_from_high_pct: Optional[float] = None
    macro_cycle: str
    macro_phase: str
    price_phase: str
    signal: SignalAction
    confidence: float = Field(ge=0, le=100)
    rationale: str
    updated_at: datetime


class MarketSummary(BaseModel):
    total_assets: int
    by_signal: dict[str, int]
    by_class: dict[str, int]
    by_region: dict[str, int]
    avg_confidence: float
    outlook: str
    outlook_label: str


class ChartCandle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class ChartResponse(BaseModel):
    symbol: str
    name: str
    interval: str
    range: str
    currency: str = "USD"
    candles: list[ChartCandle]
    current_price: float
    change: float
    change_pct: float
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    prev_close: Optional[float] = None


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


class RegionalCycleSnapshot(BaseModel):
    region: str
    region_label: str
    cycle_id: str
    phase: str
    signal: SignalAction
    buy_weight: float
    bias: str
    rationale: str


class DashboardResponse(BaseModel):
    bitcoin_cycle: BitcoinCycleStatus
    presidential_cycle: PresidentialCycleStatus
    regional_cycles: list[RegionalCycleSnapshot]
    opportunities: list[Opportunity]
    monitored_assets: list[AssetQuote]
    market_assessments: list[AssetCycleAssessment]
    market_summary: MarketSummary
    last_scan_at: Optional[datetime] = None
    last_price_tick_at: Optional[datetime] = None
    live_mode: bool = False
    scanner_running: bool
    scan_in_progress: bool = False


class AlertSettings(BaseModel):
    phone: str = ""
    sms_enabled: bool = False
    push_enabled: bool = True
    ntfy_enabled: bool = True
    ntfy_topic: str = ""
    min_confidence: float = Field(default=60, ge=40, le=95)
    alert_on_signal_change: bool = True
    alert_on_new_opportunity: bool = True


class TwilioConfigRequest(BaseModel):
    account_sid: str
    auth_token: str
    from_number: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict[str, str]


class NotificationStatus(BaseModel):
    push_configured: bool
    sms_configured: bool
    ntfy_configured: bool
    ntfy_subscribe_url: str
    ntfy_app_url: str
    vapid_public_key: str
    push_subscriptions: int
    settings: AlertSettings


class PaperOrderRequest(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float | None = Field(default=None, gt=0)
    amount_pln: float | None = Field(default=None, gt=0)


class PaperPositionView(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    quantity: float
    avg_price_native: float
    avg_price_pln: float
    current_price_native: float
    current_price_pln: float
    market_value_pln: float
    cost_basis_pln: float
    unrealized_pnl_pln: float
    unrealized_pnl_pct: float
    currency: str


class PaperTradeView(BaseModel):
    id: int
    symbol: str
    name: str
    asset_class: str
    side: str
    quantity: float
    price_native: float
    price_pln: float
    total_pln: float
    fee_pln: float
    currency: str
    created_at: str


class PaperPortfolio(BaseModel):
    cash_pln: float
    initial_cash_pln: float
    positions_value_pln: float
    total_equity_pln: float
    unrealized_pnl_pln: float
    realized_pnl_pln: float
    total_pnl_pln: float
    total_pnl_pct: float
    usd_pln_rate: float
    positions_count: int
    positions: list[PaperPositionView]
    recent_trades: list[PaperTradeView]
    quotes_available: int
