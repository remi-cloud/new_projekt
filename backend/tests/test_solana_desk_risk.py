"""Checker rejects risky mints and stays shut when the report is incomplete."""

from app.solana_desk.market import apply_rugcheck
from app.solana_desk.models import DEFAULT_SETTINGS, TokenView
from app.solana_desk.risk import assess_risk


def token(**overrides) -> TokenView:
    base = dict(
        mint="Mint111pump",
        symbol="OK",
        price_usd=0.002,
        liquidity_usd=8_000,
        volume_usd=2_500,
        age_minutes=40,
        venue="pump_fun",
        mint_authority_active=False,
        freeze_authority_active=False,
        top_holder_pct=9,
        top10_holder_pct=42,
        dev_holder_pct=1.5,
        buy_tax_pct=0,
        sell_tax_pct=0,
        can_sell=True,
        risk_ready=True,
    )
    base.update(overrides)
    return TokenView(**base)


def test_clean_token_passes():
    verdict = assess_risk(token(), DEFAULT_SETTINGS)
    assert verdict.ok
    assert verdict.reasons == ()


def test_active_mint_and_freeze_are_rejected():
    mint = assess_risk(token(mint_authority_active=True), DEFAULT_SETTINGS)
    freeze = assess_risk(token(freeze_authority_active=True), DEFAULT_SETTINGS)
    assert "aktywne uprawnienie mint" in mint.reasons
    assert "aktywne uprawnienie freeze" in freeze.reasons


def test_unknown_authority_fails_closed():
    verdict = assess_risk(token(mint_authority_active=None, risk_ready=False), DEFAULT_SETTINGS)
    assert not verdict.ok
    assert "nieznane uprawnienie mint" in verdict.reasons
    assert "brak raportu ryzyka" in verdict.reasons


def test_holder_dev_and_tax_thresholds():
    holder = assess_risk(token(top_holder_pct=31), DEFAULT_SETTINGS)
    top10 = assess_risk(token(top10_holder_pct=71), DEFAULT_SETTINGS)
    dev = assess_risk(token(dev_holder_pct=11), DEFAULT_SETTINGS)
    tax = assess_risk(token(sell_tax_pct=12), DEFAULT_SETTINGS)
    honeypot = assess_risk(token(can_sell=False), DEFAULT_SETTINGS)
    assert "największy holder" in holder.reasons[0]
    assert "top 10" in top10.reasons[0]
    assert "portfel dev" in dev.reasons[0]
    assert any("sprzedaży" in reason for reason in tax.reasons)
    assert any("honeypot" in reason for reason in honeypot.reasons)


def test_liquidity_age_and_volume():
    thin = assess_risk(token(liquidity_usd=100), DEFAULT_SETTINGS)
    young = assess_risk(token(age_minutes=1), DEFAULT_SETTINGS)
    quiet = assess_risk(token(volume_usd=10), DEFAULT_SETTINGS)
    assert "za mała płynność" in thin.reasons
    assert "token za młody" in young.reasons
    assert "za mały wolumen" in quiet.reasons


def test_rugcheck_report_marks_a_dangerous_creator():
    parsed = apply_rugcheck(
        token(risk_ready=False, top_holder_pct=None, dev_holder_pct=None),
        {
            "mintAuthority": None,
            "freezeAuthority": None,
            "creator": "DevWallet111",
            "rugged": False,
            "risks": [{"name": "Creator history of rugged tokens", "level": "danger"}],
            "topHolders": [
                {"address": "Whale", "owner": "Whale", "pct": 12},
                {"address": "DevWallet111", "owner": "DevWallet111", "pct": 4},
            ],
            "transferFee": {"pct": 0},
            "totalMarketLiquidity": 9000,
            "price": 0.002,
            "markets": [{"marketType": "pump_fun", "pubkey": "Pool111"}],
        },
    )
    verdict = assess_risk(parsed, DEFAULT_SETTINGS)
    assert parsed.rugged is True
    assert parsed.risk_ready is True
    assert not verdict.ok
    assert "oznaczenie rug" in verdict.reasons
