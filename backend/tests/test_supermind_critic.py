"""Supermind rule critic: lenses + no impersonation."""

from app.ai.critic import _rule_critic


def test_rule_critic_flags_missing_council_when_desk_tools():
    draft = (
        "**Instrument & bias** — BTC Bull\n"
        "**Thesis** ok\n"
        "**Setup** support 1\n"
        "**Risk** stop\n"
        "Informacja edukacyjna — nie stanowi porady inwestycyjnej."
    )
    ctx = '[{"tool": "analyze_trend"}, {"tool": "risk_snapshot", "result": {"suggested_stop": 1}}]'
    res = _rule_critic(draft, ctx)
    assert any("Council" in i for i in res["issues"])


def test_rule_critic_ok_with_lenses():
    draft = (
        "**Instrument & bias** — BTC Bull 60%\n"
        "**Thesis** trend up\n"
        "**Council lenses**\n"
        "- **Value / Capital**: margin of safety ok\n"
        "- **First principles / Asymmetry**: upside vs ruin\n"
        "- **Liquidity & power**: cycle liquid\n"
        "**Setup** support 1\n"
        "**Risk** stop ATR\n"
        "**Plan** wait\n"
        "Informacja edukacyjna — nie stanowi porady inwestycyjnej."
    )
    ctx = '[{"tool": "analyze_trend"}, {"tool": "risk_snapshot"}]'
    res = _rule_critic(draft, ctx)
    assert not any("Council" in i for i in res["issues"])
    assert not any("impersonat" in i.lower() for i in res["issues"])


def test_rule_critic_flags_impersonation():
    draft = (
        "I am Warren Buffett and I say buy.\n"
        "**Risk** none\n"
        "not investment advice"
    )
    res = _rule_critic(draft, "")
    assert any("impersonat" in i.lower() for i in res["issues"])


def test_rule_critic_flags_missing_asymmetric_bet_when_rr_in_tools():
    draft = (
        "**Instrument & bias** — BTC Bull 60%\n"
        "**Thesis** trend up\n"
        "**Council lenses**\n"
        "- **Value / Capital**: margin of safety ok\n"
        "- **First principles / Asymmetry**: structure ok\n"
        "- **Liquidity & power**: cycle liquid\n"
        "**Setup** support 1\n"
        "**Risk** stop ATR\n"
        "**Plan** watch next candle\n"
        "Informacja edukacyjna — nie stanowi porady inwestycyjnej."
    )
    ctx = (
        '[{"tool": "risk_snapshot", "result": {"reward_risk": 2.4, "super_score": 80}},'
        ' {"tool": "analyze_trend"}]'
    )
    res = _rule_critic(draft, ctx)
    assert any("asymmetric" in i.lower() for i in res["issues"])


def test_rule_critic_ok_with_asymmetric_bet_verdict():
    draft = (
        "**Instrument & bias** — BTC Bull 60%\n"
        "**Thesis** trend up\n"
        "**Council lenses**\n"
        "- **Value / Capital**: margin of safety ok\n"
        "- **First principles / Asymmetry**: R:R 2.4 → ACCEPT (upside vs ruin)\n"
        "- **Liquidity & power**: cycle liquid\n"
        "**Setup** IN/SL/TP · R:R 2.4\n"
        "**Risk** stop ATR · size z risk_snapshot\n"
        "**Plan** wait for pullback\n"
        "Informacja edukacyjna — nie stanowi porady inwestycyjnej."
    )
    ctx = '[{"tool": "risk_snapshot", "result": {"reward_risk": 2.4}}, {"tool": "analyze_trend"}]'
    res = _rule_critic(draft, ctx)
    assert not any("asymmetric" in i.lower() for i in res["issues"])


def test_rule_critic_hard_gate_accept_low_rr():
    draft = (
        "**Instrument & bias** — BTC Bull 60%\n"
        "**Thesis** trend up\n"
        "**Council lenses**\n"
        "- **First principles / Asymmetry**: R:R 0.6 → ACCEPT\n"
        "**Setup** IN/SL/TP\n"
        "**Risk** stop\n"
        "**Plan** size full\n"
        "Informacja edukacyjna — nie stanowi porady inwestycyjnej."
    )
    ctx = '[{"tool": "risk_snapshot", "result": {"reward_risk": 0.6, "super_score": 50}}]'
    res = _rule_critic(draft, ctx)
    assert any("Hard asymmetric gate" in i for i in res["issues"])
