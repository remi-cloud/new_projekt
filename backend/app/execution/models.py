"""Pydantic models for broker execution agent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProposalStatus = Literal[
    "pending",
    "approved",
    "executed",
    "dry_run",
    "skipped",
    "skipped_no_credentials",
    "skipped_risk",
    "failed",
]

SignalSource = Literal["opportunity", "pearl"]


class SignalCandidate(BaseModel):
    symbol: str
    name: str
    asset_class: str
    region: str = "global"
    source: SignalSource
    confidence: float = Field(ge=0, le=100)
    price: float = 0.0
    rationale: str = ""


class BrokerOrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"] = "buy"
    quantity: float | None = None
    amount_pln: float | None = None
    asset_class: str = "stock"


class BrokerOrderResult(BaseModel):
    success: bool
    order_id: str | None = None
    filled_qty: float | None = None
    fill_price: float | None = None
    message: str = ""
    dry_run: bool = False


class BrokerPosition(BaseModel):
    symbol: str
    quantity: float
    avg_price: float | None = None


class BrokerStatus(BaseModel):
    broker_id: str
    name: str
    configured: bool
    connected: bool = False
    notes: str = ""


class TradeProposal(BaseModel):
    id: int | None = None
    symbol: str
    name: str
    asset_class: str
    region: str = "global"
    broker_id: str
    source: SignalSource
    confidence: float
    amount_pln: float
    rationale: str = ""
    status: ProposalStatus = "pending"
    broker_order_id: str | None = None
    paper_trade_id: int | None = None
    error_message: str | None = None
    created_at: datetime
    executed_at: datetime | None = None


class ExecutionSettingsView(BaseModel):
    enabled: bool
    dry_run: bool
    mirror_paper: bool
    require_approval: bool
    min_confidence: float
    amount_pln: float
    max_daily: int
    cooldown_hours: int
    broker_crypto: str
    broker_equity: str
    broker_equity_fallback: str


class ExecutionStatus(BaseModel):
    enabled: bool
    dry_run: bool
    mirror_paper: bool
    require_approval: bool
    proposals_today: int
    max_daily: int
    last_run_at: str | None = None
    settings: ExecutionSettingsView
    brokers: list[BrokerStatus]


class ExecutionRunResult(BaseModel):
    processed: int
    created: int
    executed: int
    skipped: int
    errors: int
