"""Binance Spot adapter — read-only balances; dry-run orders until live enabled."""

from __future__ import annotations

from app.config import settings
from app.data.whale_flows import BINANCE_SYMBOLS
from app.execution.brokers.stub import StubBrokerAdapter
from app.execution.models import BrokerOrderRequest, BrokerOrderResult, BrokerPosition
from app.integrations.binance_spot import binance_configured, fetch_spot_balances


class BinanceAdapter(StubBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("binance", "Binance", configured=binance_configured())

    async def is_connected(self) -> bool:
        if not await self.is_configured():
            return False
        balances = await fetch_spot_balances()
        return balances is not None

    async def get_balance(self, currency: str) -> float:
        if not await self.is_configured():
            return 0.0
        cur = currency.upper()
        for row in await fetch_spot_balances():
            if row.get("asset") == cur:
                return float(row.get("free") or 0)
        return 0.0

    async def get_open_positions(self) -> list[BrokerPosition]:
        if not await self.is_configured():
            return []
        reverse = {v: k for k, v in BINANCE_SYMBOLS.items()}
        out: list[BrokerPosition] = []
        for row in await fetch_spot_balances():
            asset = str(row.get("asset") or "")
            qty = float(row.get("total") or 0)
            if qty <= 0:
                continue
            pair = f"{asset}USDT"
            symbol = reverse.get(pair)
            if not symbol:
                if asset in ("USDT", "USDC", "BUSD"):
                    continue
                symbol = f"{asset}-USD"
            out.append(BrokerPosition(symbol=symbol, quantity=qty, avg_price=None))
        return out

    async def place_market_order(self, req: BrokerOrderRequest, *, dry_run: bool) -> BrokerOrderResult:
        if not await self.is_configured():
            return BrokerOrderResult(
                success=False,
                message="Binance not configured — set CYCLICAL_BINANCE_API_KEY and CYCLICAL_BINANCE_API_SECRET",
            )
        if dry_run or getattr(settings, "binance_ai_bot_dry_run", True):
            return await super().place_market_order(req, dry_run=True)
        return BrokerOrderResult(
            success=False,
            message="Binance live execution not enabled — keep CYCLICAL_BINANCE_AI_BOT_DRY_RUN=true",
            dry_run=True,
        )
