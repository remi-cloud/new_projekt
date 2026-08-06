"""Dry-run broker adapter — simulates fills without real API calls."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.execution.models import BrokerOrderRequest, BrokerOrderResult, BrokerPosition


class StubBrokerAdapter:
    """Simulates order execution for dry-run and unconfigured brokers."""

    def __init__(self, broker_id: str, name: str, *, configured: bool = False) -> None:
        self.broker_id = broker_id
        self.name = name
        self._configured = configured

    async def is_configured(self) -> bool:
        return self._configured

    async def is_connected(self) -> bool:
        return self._configured

    async def get_balance(self, currency: str) -> float:
        return 1_000_000.0 if currency.upper() == "PLN" else 250_000.0

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult:
        order_id = f"stub-{self.broker_id}-{uuid.uuid4().hex[:12]}"
        qty = req.quantity or 1.0
        return BrokerOrderResult(
            success=True,
            order_id=order_id,
            filled_qty=qty,
            fill_price=req.amount_pln / qty if req.amount_pln and qty else None,
            message=f"Stub fill @ {datetime.now(timezone.utc).isoformat()}",
            dry_run=dry_run or not self._configured,
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_open_positions(self) -> list[BrokerPosition]:
        return []
