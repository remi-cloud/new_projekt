from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

MacroNewsCategory = Literal["fed", "usa", "macro", "global", "musk"]


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


class PresidentialYearReturn(BaseModel):
    year: PresidentialYear
    year_number: int
    label: str
    avg_return_pct: float
    vs_cycle_avg_pct: float
    bias: str
    tone: str
    is_current: bool = False


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
    benchmark: str = "S&P 500"
    benchmark_note: str = "Średni roczny zwrot w latach cyklu (1949–2024, Stock Trader's Almanac)"
    cycle_avg_return_pct: float = 8.5
    year_returns: list[PresidentialYearReturn] = Field(default_factory=list)
    current_year_expected_return_pct: float = 0.0


class AssetQuote(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    price: float
    change_pct_24h: Optional[float] = None
    change_pct_7d: Optional[float] = None
    currency: str = "USD"
    updated_at: datetime


class BrokerOption(BaseModel):
    id: str
    name: str
    regions: list[str] = Field(default_factory=list)
    url: str = ""
    notes: str = ""


class BrokerPurchaseInfo(BaseModel):
    primary_exchange: str | None = None
    brokers: list[BrokerOption] = Field(default_factory=list)
    disclaimer: str = ""


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
    momentum_score: Optional[float] = None
    momentum_signal: Optional[SignalAction] = None
    momentum_phase: Optional[str] = None
    is_momentum_pick: bool = False
    signal: SignalAction
    confidence: float = Field(ge=0, le=100)
    rationale: str
    updated_at: datetime
    broker_info: Optional[BrokerPurchaseInfo] = None


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


class CycleMarker(BaseModel):
    time: int
    action: SignalAction
    confidence: float = Field(ge=0, le=100)
    price: float
    rationale: str


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
    cycle_markers: list[CycleMarker] = Field(default_factory=list)


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
    momentum_score: Optional[float] = None
    momentum_signal: Optional[SignalAction] = None
    is_momentum_pick: bool = False
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


class MacroNewsItem(BaseModel):
    id: str
    title: str
    summary: str | None = None
    url: str | None = None
    image_url: str | None = None
    source_image_url: str | None = None
    source: str
    category: MacroNewsCategory
    impact: str = "medium"
    published_at: datetime
    is_curated: bool = False
    age_minutes: int | None = None


class MacroCalendarEvent(BaseModel):
    id: str
    title: str
    event_date: date
    days_until: int
    category: str
    impact: str = "high"
    time_utc: str = "13:30"
    region: str = "US"


class MacroCalendarMonthResponse(BaseModel):
    year: int
    month: int
    events: list[MacroCalendarEvent]
    news: list[MacroNewsItem] = Field(default_factory=list)
    fetched_at: datetime
    poll_interval_seconds: int = 120


class MacroNewsFeed(BaseModel):
    items: list[MacroNewsItem]
    calendar_events: list[MacroCalendarEvent] = Field(default_factory=list)
    fetched_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    sources_count: int = 0
    poll_interval_seconds: int = 120
    fresh_count_1h: int = 0


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
    alert_on_macro_news: bool = True


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
    order_type: str = Field(default="market", pattern="^(market|limit|stop|take_profit)$")
    limit_price_native: float | None = Field(default=None, gt=0)


class PaperCloseRequest(BaseModel):
    percent: float = Field(default=100.0, ge=10.0, le=100.0)


class PaperPositionView(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    quantity: float
    is_short: bool = False
    avg_price_native: float
    avg_price_pln: float
    current_price_native: float
    current_price_pln: float
    market_value_pln: float
    cost_basis_pln: float
    unrealized_pnl_pln: float
    unrealized_pnl_pct: float
    currency: str
    opened_at: str | None = None
    pending_limit_orders: list["PaperLimitOrderView"] = Field(default_factory=list)
    broker_info: BrokerPurchaseInfo | None = None


class PearlFind(BaseModel):
    id: int | None = None
    agent_id: str
    symbol: str
    name: str
    asset_class: AssetClass
    region: str = "global"
    price: float = 0.0
    change_pct_24h: float | None = None
    score: float = 0.0
    confidence: float = 0.0
    action: SignalAction = "watch"
    rationale: str = ""
    source: str = ""
    found_at: datetime
    broker_info: BrokerPurchaseInfo | None = None


class PearlHunterStatus(BaseModel):
    enabled: bool
    agents: list[dict] = Field(default_factory=list)
    finds_count: int = 0
    last_run_at: datetime | None = None


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


class PaperLimitOrderView(BaseModel):
    id: int
    symbol: str
    name: str
    asset_class: AssetClass
    side: str
    order_type: str = "limit"
    limit_price_native: float
    limit_price_pln: float
    amount_pln: float
    quantity_est: float
    currency: str
    status: str
    created_at: str


class PaperClosedPositionView(BaseModel):
    id: int
    symbol: str
    name: str
    asset_class: AssetClass
    quantity: float
    is_short: bool = False
    entry_price_native: float
    exit_price_native: float
    entry_price_pln: float
    exit_price_pln: float
    cost_basis_pln: float
    proceeds_pln: float
    realized_pnl_pln: float
    realized_pnl_pct: float
    currency: str
    opened_at: str
    closed_at: str


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
    closed_positions_count: int = 0
    closed_positions: list[PaperClosedPositionView] = Field(default_factory=list)
    limit_orders: list[PaperLimitOrderView] = []
    recent_trades: list[PaperTradeView]
    quotes_available: int


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    locale: str = "pl"
    symbol: str | None = None


class AiChatResponse(BaseModel):
    session_id: str
    reply: str
    message_id: int
    tools_used: list[str] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    critic_score: float | None = None
    llm_active: bool = False
    tool_count: int = 0


class AiFeedbackRequest(BaseModel):
    session_id: str
    message_id: int | None = None
    rating: int = Field(ge=1, le=5)
    correction: str | None = None
    question: str | None = None
    answer: str | None = None


class AiStatusResponse(BaseModel):
    enabled: bool
    llm_configured: bool
    model: str
    features: list[str]
    knowledge_entries: int = 0
    learning_notes: int = 0


class AiAnalyzeResponse(BaseModel):
    symbol: str
    summary: str
    tools: list[dict] = Field(default_factory=list)
    llm_active: bool = False


class RoiCalculateRequest(BaseModel):
    symbol: str
    amount: float = Field(gt=0, le=100_000_000)
    strategy: str = "buy_hold"  # buy_hold | cycle | dca | cycle_dca
    mode: str = "forward"  # forward | backtest
    years: int = Field(default=30, ge=1, le=50)
    monthly_contribution: float = Field(default=0, ge=0, le=10_000_000)
    start: date | None = None
    end: date | None = None
    compare_buy_hold: bool = True


class RoiAssetInfo(BaseModel):
    symbol: str
    name: str
    asset_class: str
    region: str
    history_from: str


class NewsletterRequest(BaseModel):
    email: str
    locale: str | None = None
    source: str = "web"


class BusinessLeadRequest(BaseModel):
    name: str
    email: str
    company: str | None = None
    package: str | None = None
    message: str | None = None
    locale: str | None = None


class WatchlistVoteRequest(BaseModel):
    symbol: str
    name: str | None = None

