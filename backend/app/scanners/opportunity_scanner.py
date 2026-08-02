"""Opportunity scanner facade — delegates to multi-agent orchestrator."""

from __future__ import annotations

import logging

from app.agents.orchestrator import orchestrator
from app.models.schemas import (
    AlphaModelStatus,
    AssetQuote,
    BetaModelStatus,
    Opportunity,
)

logger = logging.getLogger(__name__)


class OpportunityScanner:
    """
    Backward-compatible facade.
    Real work: 6 LONG + 6 SHORT global scouts → 2 AI specialists → orchestrator.
    """

    def __init__(self) -> None:
        self._orch = orchestrator

    @property
    def last_scan_at(self):
        return self._orch.last_scan_at

    @last_scan_at.setter
    def last_scan_at(self, value) -> None:
        self._orch.last_scan_at = value

    @property
    def opportunities(self) -> list[Opportunity]:
        return self._orch.opportunities

    @opportunities.setter
    def opportunities(self, value: list[Opportunity]) -> None:
        self._orch.opportunities = value

    @property
    def alpha_model(self) -> AlphaModelStatus | None:
        return self._orch.alpha_model

    @alpha_model.setter
    def alpha_model(self, value: AlphaModelStatus | None) -> None:
        self._orch.alpha_model = value

    @property
    def beta_model(self) -> BetaModelStatus | None:
        return self._orch.beta_model

    @beta_model.setter
    def beta_model(self, value: BetaModelStatus | None) -> None:
        self._orch.beta_model = value

    @property
    def quotes(self) -> list[AssetQuote]:
        return self._orch.quotes

    @quotes.setter
    def quotes(self, value: list[AssetQuote]) -> None:
        self._orch.quotes = value

    @property
    def bitcoin_cycle(self) -> AlphaModelStatus | None:
        return self._orch.bitcoin_cycle

    @property
    def presidential_cycle(self) -> BetaModelStatus | None:
        return self._orch.presidential_cycle

    async def scan(self) -> list[Opportunity]:
        logger.info("Scanner → multi-agent orchestrator pipeline")
        return await self._orch.scan()


scanner = OpportunityScanner()
