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
