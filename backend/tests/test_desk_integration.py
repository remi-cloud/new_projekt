from app.coordinator.link_guard import audit_axiom_urls, audit_terminal_urls, link_guard_bad_count, link_guard_ok
from app.launch_scout.service import _split_tick_errors


def test_split_tick_errors_core_vs_warnings():
    errors = ["pump_traders: timeout", "dex_profiles: dns fail", "wallet_scout: rpc err", "session_clock: x"]
    core, warnings = _split_tick_errors(errors)
    assert core == ["pump_traders: timeout", "wallet_scout: rpc err"]
    assert warnings == ["dex_profiles: dns fail", "session_clock: x"]


def test_link_guard_total_includes_axiom():
    lg = {"bad_4meme": 0, "missing_chain_axiom": 0, "axiom_missing_chain": 2}
    assert link_guard_bad_count(lg) == 2
    assert link_guard_ok(lg) is False


def test_link_guard_merge_axiom_audit():
    launch = audit_terminal_urls([{"chain": "solana", "url": "https://axiom.trade/meme/x?chain=sol&pulseChains=sol"}])
    axiom = audit_axiom_urls(
        [{"url": "https://axiom.trade/meme/y"}],
        [],
    )
    merged = {**launch, "axiom_missing_chain": axiom["missing_chain_axiom"]}
    assert link_guard_bad_count(merged) == 1
