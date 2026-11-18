from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

MacroNewsCategory = Literal["fed", "usa", "macro", "global", "musk", "crypto"]


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    STOCK = "stock"
    ETF = "etf"
    TOKENIZED = "tokenized"
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


class BtcSpxComparison(BaseModel):
    corr_full: float | None = None
    corr_rolling_24m_latest: float | None = None
    best_six_delta_pct: float | None = None
    month_sign_agreement: int | None = None
    verdict: str = "partially"  # similar_to_spx | partially | idiosyncratic
    regime: str = "mixed"  # equity_beta | mixed | crypto_idiosyncratic


class BitcoinMonthReturn(BaseModel):
    month: int
    avg_return_pct: float
    bias: str  # up | down | neutral
    is_current: bool = False
    n: int = 0


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
    month_returns: list[BitcoinMonthReturn] = Field(default_factory=list)
    current_month_avg_return_pct: float | None = None
    current_month_bias: str = "neutral"
    phase_month_bias: str = "neutral"
    seasonality_sample_count: int = 0
    calendar_season: str = "best_six"  # comparison label only (US Almanac)
    spx_comparison: BtcSpxComparison | None = None


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


class InstrumentCommunity(BaseModel):
    """Direct community / social links for an instrument (X always present)."""

    x: str
    x_official: bool = False
    telegram: Optional[str] = None
    discord: Optional[str] = None
    website: Optional[str] = None
    x_community: Optional[str] = None


class InstrumentSeasonality(BaseModel):
    """Same contract for every instrument — unavailable when region has no matrix."""

    available: bool = False
    bias: str | None = None  # up | down | neutral
    avg_pct: float | None = None
    source: str | None = None  # symbol|class|universe|phase|calendar|unavailable
    n: int | None = None
    calendar_season: str | None = None  # best_six | worst_six
    reason: str | None = None


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
    tags: list[str] = Field(default_factory=list)
    chain: Optional[str] = None
    related_symbols: list[str] = Field(default_factory=list)
    community: Optional[InstrumentCommunity] = None
    seasonality: Optional[InstrumentSeasonality] = None


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
    community: Optional[InstrumentCommunity] = None


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


class MacroNewsFeed(BaseModel):
    items: list[MacroNewsItem]
    fetched_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    sources_count: int = 0
    poll_interval_seconds: int = 120
    fresh_count_1h: int = 0


class DashboardResponse(BaseModel):
    bitcoin_cycle: BitcoinCycleStatus
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
    ntfy_enabled: bool = False
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
    image_url: str | None = None
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
    image_url: str | None = None


class PaperTradeStats(BaseModel):
    trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float | None = None
    avg_win_pln: float | None = None
    avg_loss_pln: float | None = None
    expectancy_pln: float | None = None
    best_pln: float | None = None
    worst_pln: float | None = None


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
    trade_stats: PaperTradeStats | None = None
    limit_orders: list[PaperLimitOrderView] = []
    recent_trades: list[PaperTradeView]
    quotes_available: int


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=80)
    locale: str = Field(default="pl", max_length=12)
    symbol: str | None = Field(default=None, max_length=32)


class AiChatResponse(BaseModel):
    session_id: str
    reply: str
    message_id: int
    tools_used: list[str] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    critic_score: float | None = None
    llm_active: bool = False
    tool_count: int = 0
    focus_symbol: str | None = None
    desk_ui: dict | None = None


class AiFeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=80)
    message_id: int | None = None
    rating: int = Field(ge=1, le=5)
    correction: str | None = Field(default=None, max_length=2000)
    question: str | None = Field(default=None, max_length=4000)
    answer: str | None = Field(default=None, max_length=8000)


class AiStatusResponse(BaseModel):
    enabled: bool
    llm_configured: bool
    model: str
    provider: str = "none"
    base_url: str = ""
    requires_api_key: bool = True
    features: list[str]
    knowledge_entries: int = 0
    learning_notes: int = 0
    free_chain: list[str] = Field(default_factory=list)


class AiAnalyzeResponse(BaseModel):
    symbol: str
    summary: str
    tools: list[dict] = Field(default_factory=list)
    llm_active: bool = False
    focus_symbol: str | None = None
    desk_ui: dict | None = None


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
    email: str = Field(min_length=3, max_length=200)
    locale: str | None = Field(default=None, max_length=12)
    source: str = Field(default="web", max_length=40)


class BusinessLeadRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    company: str | None = Field(default=None, max_length=160)
    package: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=4000)
    locale: str | None = Field(default=None, max_length=12)


class WatchlistVoteRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    name: str | None = Field(default=None, max_length=80)


# ── Scanner desk (heatmap / Superokazje / Singularity) ─────────────────


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
    preview: bool = False


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


class AiTradeFactor(BaseModel):
    name: str
    side: str
    weight: float
    detail: str


class AiTradeSignal(BaseModel):
    signal: str
    label: str
    confidence: float
    buy_score: float
    sell_score: float
    aligned: bool = False
    conflict: bool = False
    summary: str
    factors: list[AiTradeFactor] = Field(default_factory=list)
    verdict_detail: str = ""


class WhaleFlowSignal(BaseModel):
    symbol: str
    bias: str
    side_hint: str = "neutral"
    strength: float = 0
    score: float = 0
    summary: str = ""
    factors: list[str] = Field(default_factory=list)
    updated_at: Optional[str] = None


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
    ai_signal: Optional[AiTradeSignal] = None
    whale: Optional[WhaleFlowSignal] = None
    reasons: list[str]
    rationale: str
    updated_at: str
    community: Optional[InstrumentCommunity] = None


class SuperOpportunitiesResponse(BaseModel):
    generated_at: str
    count: int
    super_count: int
    long_count: int = 0
    short_count: int = 0
    items: list[SuperOpportunity]
    supers: list[SuperOpportunity]
    scanner_last_scan_at: Optional[str] = None


class AlphaModelStatus(BaseModel):
    """Adapter shape for Singularity scouts (maps from Bitcoin cycle)."""

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
    """Singularity beta scout. Neutral while the presidential cycle is off."""

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

