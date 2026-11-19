"""Jupiter quotes with a Raydium fallback. No broadcast lives here."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

SOL_MINT = "So11111111111111111111111111111111111111112"
RAYDIUM_QUOTE = "https://transaction-v1.raydium.io/compute/swap-base-in"
RAYDIUM_SWAP = "https://transaction-v1.raydium.io/transaction/swap-base-in"


class QuoteUnavailable(RuntimeError):
    """Both venues failed to answer."""


class NoRoute(RuntimeError):
    """A venue answered and there is no route."""


@dataclass
class RouteQuote:
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    impact_pct: float
    platform_fee_lamports: int
    venue: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def price_sol_per_token(self) -> float:
        if self.out_amount <= 0 or self.in_amount <= 0:
            return 0.0
        if self.input_mint == SOL_MINT:
            return (self.in_amount / 1_000_000_000) / self.out_amount
        return (self.out_amount / 1_000_000_000) / self.in_amount


def impact_pct(raw: object) -> float:
    """Jupiter lite documents priceImpactPct as a fraction (0.02 = 2%)."""
    try:
        value = abs(float(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if value <= 1:
        return value * 100.0
    return value


def jupiter_base() -> str:
    explicit = os.environ.get("JUPITER_BASE", "").strip()
    if explicit:
        return explicit.rstrip("/")
    if os.environ.get("JUPITER_API_KEY", "").strip():
        return "https://api.jup.ag/swap/v1"
    return "https://lite-api.jup.ag/swap/v1"


def jupiter_headers() -> dict[str, str]:
    key = os.environ.get("JUPITER_API_KEY", "").strip()
    if not key:
        return {}
    return {"x-api-key": key}


def _parse_amounts(data: dict) -> tuple[int, int, float, int]:
    block = data.get("data") if isinstance(data.get("data"), dict) else data
    in_raw = block.get("inAmount") or block.get("inputAmount") or data.get("inAmount")
    out_raw = block.get("outAmount") or block.get("outputAmount") or data.get("outAmount")
    impact = block.get("priceImpactPct", data.get("priceImpactPct", 0))
    fee = block.get("platformFee") or data.get("platformFee") or {}
    fee_amount = 0
    if isinstance(fee, dict):
        fee_amount = int(float(fee.get("amount") or 0))
    elif fee:
        fee_amount = int(float(fee))
    return int(float(in_raw or 0)), int(float(out_raw or 0)), impact_pct(impact), fee_amount


class QuoteRouter:
    """Subclass or replace in tests. Production uses HttpQuoteRouter."""

    async def quote(self, *, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> RouteQuote:
        raise QuoteUnavailable("no quote: jupiter+raydium down")

    async def build_swap(self, quote: RouteQuote, user_pubkey: str, priority_lamports: int) -> str:
        raise QuoteUnavailable("no swap build")

    async def rpc(self, method: str, params: list) -> dict:
        raise QuoteUnavailable("no rpc")

    async def priority_fee_lamports(self, fallback: int, cap: int = 10_000_000) -> int:
        return max(0, min(int(fallback), cap))


class HttpQuoteRouter(QuoteRouter):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def quote(self, *, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> RouteQuote:
        errors: list[str] = []
        try:
            return await self._jupiter_quote(input_mint, output_mint, amount, slippage_bps)
        except NoRoute:
            raise
        except Exception as exc:  # noqa: BLE001 — fall through to Raydium
            errors.append(exc.__class__.__name__)
        try:
            return await self._raydium_quote(input_mint, output_mint, amount, slippage_bps)
        except NoRoute:
            raise
        except Exception as exc:  # noqa: BLE001
            errors.append(exc.__class__.__name__)
        raise QuoteUnavailable("no quote: jupiter+raydium down")

    async def build_swap(self, quote: RouteQuote, user_pubkey: str, priority_lamports: int) -> str:
        if quote.venue == "raydium":
            return await self._raydium_swap(quote, user_pubkey, priority_lamports)
        return await self._jupiter_swap(quote, user_pubkey, priority_lamports)

    async def rpc(self, method: str, params: list) -> dict:
        url = os.environ.get("SOLANA_RPC_URL", "").strip()
        if not url:
            raise QuoteUnavailable("no rpc")
        async with self._http() as client:
            response = await client.post(
                url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or data.get("error"):
            raise QuoteUnavailable("rpc error")
        return data

    async def priority_fee_lamports(self, fallback: int, cap: int = 10_000_000) -> int:
        try:
            data = await self.rpc("getRecentPrioritizationFees", [])
            fees = [
                int(item.get("prioritizationFee") or 0)
                for item in (data.get("result") or [])
                if isinstance(item, dict)
            ]
            if fees:
                fees.sort()
                picked = fees[min(len(fees) - 1, int(len(fees) * 0.9))]
                return max(0, min(picked, cap))
        except Exception:
            pass
        return max(0, min(int(fallback), cap))

    def _http(self):
        if self._client is not None:
            return _Reuse(self._client)
        return httpx.AsyncClient(timeout=12.0)

    async def _jupiter_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> RouteQuote:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": int(slippage_bps),
            "restrictIntermediateTokens": "true",
        }
        async with self._http() as client:
            response = await client.get(f"{jupiter_base()}/quote", params=params, headers=jupiter_headers())
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise QuoteUnavailable("jupiter")
        in_amount, out_amount, impact, fee = _parse_amounts(data)
        if out_amount <= 0:
            raise NoRoute("honeypot: sell sim failed")
        return RouteQuote(input_mint, output_mint, in_amount or amount, out_amount, impact, fee, "jupiter", data)

    async def _jupiter_swap(self, quote: RouteQuote, user_pubkey: str, priority_lamports: int) -> str:
        body = {
            "quoteResponse": quote.raw,
            "userPublicKey": user_pubkey,
            "dynamicComputeUnitLimit": True,
            "dynamicSlippage": False,
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {
                    "priorityLevel": "high",
                    "maxLamports": int(priority_lamports),
                }
            },
        }
        async with self._http() as client:
            response = await client.post(f"{jupiter_base()}/swap", json=body, headers=jupiter_headers())
            response.raise_for_status()
            data = response.json()
        tx = str((data or {}).get("swapTransaction") or "")
        if not tx:
            raise QuoteUnavailable("jupiter swap")
        return tx

    async def _raydium_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> RouteQuote:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": int(slippage_bps),
            "txVersion": "V0",
        }
        async with self._http() as client:
            response = await client.get(RAYDIUM_QUOTE, params=params)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise QuoteUnavailable("raydium")
        in_amount, out_amount, impact, fee = _parse_amounts(data)
        if out_amount <= 0:
            raise NoRoute("honeypot: sell sim failed")
        return RouteQuote(input_mint, output_mint, in_amount or amount, out_amount, impact, fee, "raydium", data)

    async def _raydium_swap(self, quote: RouteQuote, user_pubkey: str, priority_lamports: int) -> str:
        body = {
            "computeUnitPriceMicroLamports": str(priority_lamports),
            "swapResponse": quote.raw,
            "txVersion": "V0",
            "wallet": user_pubkey,
            "wrapSol": quote.input_mint == SOL_MINT,
            "unwrapSol": quote.output_mint == SOL_MINT,
        }
        async with self._http() as client:
            response = await client.post(RAYDIUM_SWAP, json=body)
            response.raise_for_status()
            data = response.json()
        txs = ((data or {}).get("data") or []) if isinstance(data, dict) else []
        if isinstance(txs, list) and txs:
            tx = txs[0].get("transaction") if isinstance(txs[0], dict) else ""
            if tx:
                return str(tx)
        raise QuoteUnavailable("raydium swap")


class _Reuse:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *_) -> None:
        return None


_installed: QuoteRouter | None = None


def install_router(router: QuoteRouter | None) -> None:
    global _installed
    _installed = router


def get_router() -> QuoteRouter:
    if _installed is not None:
        return _installed
    if os.environ.get("SOLANA_DESK_QUOTES", "auto").strip().lower() == "off":
        return _Down()
    return HttpQuoteRouter()


class _Down(QuoteRouter):
    async def quote(self, *, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> RouteQuote:
        raise QuoteUnavailable("no quote: jupiter+raydium down")
