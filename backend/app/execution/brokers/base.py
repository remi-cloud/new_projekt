"""Broker adapter protocol."""

from __future__ import annotations

from typing import Protocol

from app.execution.models import BrokerOrderRequest, BrokerOrderResult, BrokerPosition


class BrokerAdapter(Protocol):
    broker_id: str
    name: str

    async def is_configured(self) -> bool: ...

    async def is_connected(self) -> bool: ...

    async def get_balance(self, currency: str) -> float: ...

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult: ...

    async def cancel_order(self, order_id: str) -> bool: ...

    async def get_open_positions(self) -> list[BrokerPosition]: ...
