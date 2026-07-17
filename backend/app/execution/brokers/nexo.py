"""Nexo Pro adapter — stub until API keys are linked."""

from __future__ import annotations

from app.config import settings
from app.execution.brokers.stub import StubBrokerAdapter
from app.execution.models import BrokerOrderRequest, BrokerOrderResult


class NexoAdapter(StubBrokerAdapter):
    def __init__(self) -> None:
        configured = bool(settings.nexo_api_key and settings.nexo_api_secret)
        super().__init__("nexo", "Nexo", configured=configured)

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult:
        if not await self.is_configured():
            return BrokerOrderResult(
                success=False,
                message="Nexo not configured — set CYCLICAL_NEXO_API_KEY and CYCLICAL_NEXO_API_SECRET",
            )
        if dry_run:
            return await super().place_market_order(req, dry_run=True)
        return BrokerOrderResult(
            success=False,
            message="Nexo live execution not yet implemented — use dry_run",
        )
