"""eToro adapter — stub until partner / Open API is linked."""

from __future__ import annotations

from app.config import settings
from app.execution.brokers.stub import StubBrokerAdapter
from app.execution.models import BrokerOrderRequest, BrokerOrderResult


class EtoroAdapter(StubBrokerAdapter):
    def __init__(self) -> None:
        configured = bool(settings.etoro_api_key)
        super().__init__("etoro", "eToro", configured=configured)

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult:
        if not await self.is_configured():
            return BrokerOrderResult(
                success=False,
                message="eToro not configured — set CYCLICAL_ETORO_API_KEY",
            )
        if dry_run:
            return await super().place_market_order(req, dry_run=True)
        return BrokerOrderResult(
            success=False,
            message="eToro live execution not yet implemented — retail API limited",
        )
