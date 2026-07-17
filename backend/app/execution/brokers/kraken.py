"""Kraken REST adapter — stub until API keys are linked."""

from __future__ import annotations

from app.config import settings
from app.execution.brokers.stub import StubBrokerAdapter
from app.execution.models import BrokerOrderRequest, BrokerOrderResult


class KrakenAdapter(StubBrokerAdapter):
    def __init__(self) -> None:
        configured = bool(settings.kraken_api_key and settings.kraken_api_secret)
        super().__init__("kraken", "Kraken", configured=configured)

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult:
        if not await self.is_configured():
            return BrokerOrderResult(
                success=False,
                message="Kraken not configured — set CYCLICAL_KRAKEN_API_KEY and CYCLICAL_KRAKEN_API_SECRET",
            )
        if dry_run:
            return await super().place_market_order(req, dry_run=True)
        # Phase 3: POST /0/private/AddOrder
        return BrokerOrderResult(
            success=False,
            message="Kraken live execution not yet implemented — use dry_run",
        )
