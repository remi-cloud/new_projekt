"""Interactive Brokers adapter — stub until Client Portal / Gateway API is linked."""

from __future__ import annotations

from app.config import settings
from app.execution.brokers.stub import StubBrokerAdapter
from app.execution.models import BrokerOrderRequest, BrokerOrderResult


class IbkrAdapter(StubBrokerAdapter):
    def __init__(self) -> None:
        configured = bool(settings.ibkr_gateway_url and settings.ibkr_account)
        super().__init__("ibkr", "Interactive Brokers", configured=configured)

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult:
        if not await self.is_configured():
            return BrokerOrderResult(
                success=False,
                message="IBKR not configured — set CYCLICAL_IBKR_GATEWAY_URL and CYCLICAL_IBKR_ACCOUNT",
            )
        if dry_run:
            return await super().place_market_order(req, dry_run=True)
        # Phase 3: real IB Gateway / Client Portal API call
        return BrokerOrderResult(
            success=False,
            message="IBKR live execution not yet implemented — use dry_run",
        )
