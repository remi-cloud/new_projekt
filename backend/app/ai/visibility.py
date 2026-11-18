"""Paper portfolio stays on the desk. Guests still get market and news tools."""

from __future__ import annotations

from contextvars import ContextVar

desk_portfolio_visible: ContextVar[bool] = ContextVar("desk_portfolio_visible", default=False)

PRIVATE_TOOLS = frozenset({"get_paper_portfolio", "get_binance_portfolio_sync"})


def portfolio_visible() -> bool:
    return desk_portfolio_visible.get()


def hidden_portfolio() -> dict:
    return {
        "available": False,
        "reason": "Portfel papierowy jest widoczny po zalogowaniu biurka.",
    }


def redact_private_tools(tools: list) -> list:
    if portfolio_visible():
        return tools
    return [block for block in tools if block.get("tool") not in PRIVATE_TOOLS]
