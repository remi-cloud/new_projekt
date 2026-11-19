"""Flags new pairs and volume spikes. Does not trade, size, or swap."""

from __future__ import annotations

from app.solana_desk.models import TokenView, finite


def describe(token: TokenView) -> str:
    parts: list[str] = []
    if token.spike is not None and token.spike > 0:
        parts.append(f"spike {token.spike:.1f}×")
    if token.buys_pct is not None:
        parts.append(f"buys {token.buys_pct:.0f}%")
    if token.lp_locked_pct is not None:
        parts.append(f"LP {token.lp_locked_pct:.0f}% locked")
    if not parts and token.volume_5m_usd:
        parts.append(f"vol {finite(token.volume_5m_usd):.0f}")
    if not parts and token.volume_usd:
        parts.append(f"vol {finite(token.volume_usd):.0f}")
    return " · ".join(parts) if parts else "new pair"


def chip_metric(token: TokenView) -> str:
    if token.spike is not None and token.spike > 0:
        return f"spike {token.spike:.1f}×"
    if token.lp_locked_pct is not None:
        return f"LP {token.lp_locked_pct:.0f}% locked"
    if token.buys_pct is not None:
        return f"buys {token.buys_pct:.0f}%"
    if token.volume_5m_usd and token.spike:
        return f"vol {token.spike:.1f}×"
    return describe(token)


def features(token: TokenView, **extra: object) -> dict:
    base = {
        "spike": token.spike,
        "buys_pct": token.buys_pct,
        "lp_locked_pct": token.lp_locked_pct,
        "top1_pct": token.top_holder_pct,
        "top10_pct": token.top10_holder_pct,
        "dev_pct": token.dev_holder_pct,
        "age_minutes": token.age_minutes,
        "liquidity_usd": token.liquidity_usd,
        "volume_usd": token.volume_usd,
        "fade_pct": None if token.change_5m_pct is None else max(0.0, -finite(token.change_5m_pct)),
    }
    base.update(extra)
    return base
