"""Multi-agent trading pipeline types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.models.schemas import (
    AlphaModelStatus,
    AssetClass,
    AssetQuote,
    BetaModelStatus,
    Opportunity,
)

SideBias = Literal["long", "short"]
RegionClass = Literal[
    "us_equity",
    "global_equity",
    "crypto",
    "bonds",
    "commodities",
    "forex",
]

REGION_LABELS: dict[str, str] = {
    "us_equity": "US Equity / Index",
    "global_equity": "Global Equity / Index",
    "crypto": "Crypto",
    "bonds": "Bonds",
    "commodities": "Commodities",
    "forex": "Forex",
}


@dataclass(frozen=True)
class ScoutUniverse:
    region: RegionClass
    asset_classes: tuple[AssetClass, ...]
    symbols: tuple[str, ...] = ()


@dataclass
class ScoutFinding:
    scout_id: str
    side: SideBias
    region: RegionClass
    symbol: str
    name: str
    asset_class: AssetClass
    price: float
    confidence: float
    phase: str
    cycle_source: str
    rationale: str
    change_pct_7d: float | None = None
    change_pct_24h: float | None = None
    factors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SpecialistVerdict:
    side: SideBias
    symbol: str
    name: str
    asset_class: AssetClass
    accepted: bool
    confidence: float
    summary: str
    scout_ids: list[str]
    factors: list[dict[str, Any]]
    opportunity: Opportunity | None = None


@dataclass
class AgentScanResult:
    opportunities: list[Opportunity]
    long_findings: list[ScoutFinding]
    short_findings: list[ScoutFinding]
    long_verdicts: list[SpecialistVerdict]
    short_verdicts: list[SpecialistVerdict]
    alpha_model: AlphaModelStatus | None
    beta_model: BetaModelStatus | None
    quotes: list[AssetQuote]
    scanned_at: datetime
    scout_stats: dict[str, Any]
