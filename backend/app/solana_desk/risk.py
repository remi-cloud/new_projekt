"""Checker: fail closed when mint, holders, liquidity or a rug tell is missing or bad."""

from __future__ import annotations

from app.solana_desk.models import RiskVerdict, TokenView, finite


def _missing(value: float | None) -> bool:
    return value is None


def assess_risk(token: TokenView, settings: dict) -> RiskVerdict:
    reasons: list[str] = []
    if not token.risk_ready:
        reasons.append("brak raportu ryzyka")
    if token.rugged:
        reasons.append("oznaczenie rug")
    if token.mint_authority_active is None:
        reasons.append("nieznane uprawnienie mint")
    elif token.mint_authority_active:
        reasons.append("aktywne uprawnienie mint")
    if token.freeze_authority_active is None:
        reasons.append("nieznane uprawnienie freeze")
    elif token.freeze_authority_active:
        reasons.append("aktywne uprawnienie freeze")
    if token.can_sell is False:
        reasons.append("honeypot: sprzedaży nie widać")
    tax_cap = finite(settings.get("max_tax_pct"), 10)
    for label, tax in (("kupna", token.buy_tax_pct), ("sprzedaży", token.sell_tax_pct)):
        if tax is None:
            continue
        if finite(tax) > tax_cap:
            reasons.append(f"podatek {label} {finite(tax):.1f}%")
    if _missing(token.top_holder_pct):
        reasons.append("brak koncentracji holderów")
    elif finite(token.top_holder_pct) > finite(settings.get("max_top_holder_pct"), 30):
        reasons.append(f"największy holder {finite(token.top_holder_pct):.1f}%")
    if token.top10_holder_pct is not None and finite(token.top10_holder_pct) > finite(
        settings.get("max_top10_pct"), 70
    ):
        reasons.append(f"top 10 trzyma {finite(token.top10_holder_pct):.1f}%")
    if _missing(token.dev_holder_pct):
        reasons.append("brak udziału portfela dev")
    elif finite(token.dev_holder_pct) > finite(settings.get("max_dev_pct"), 10):
        reasons.append(f"portfel dev {finite(token.dev_holder_pct):.1f}%")
    if finite(token.liquidity_usd) < finite(settings.get("min_liquidity_usd"), 1500):
        reasons.append("za mała płynność")
    age = finite(token.age_minutes)
    if age < finite(settings.get("min_age_minutes"), 2):
        reasons.append("token za młody")
    max_age = finite(settings.get("max_age_hours"), 72) * 60
    if max_age > 0 and age > max_age:
        reasons.append("token za stary na to biurko")
    if finite(token.volume_usd) < finite(settings.get("min_volume_usd"), 400):
        reasons.append("za mały wolumen")
    if finite(token.price_usd) <= 0:
        reasons.append("brak ceny")
    # de-duplicate while keeping order
    unique: list[str] = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return RiskVerdict(ok=not unique, reasons=tuple(unique))
