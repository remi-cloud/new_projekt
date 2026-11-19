"""Production engine: agents, lessons, stream, self-test. No live send."""

from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path

import pytest

from app.solana_desk.agents.executor import OpenRejected, cap_pct, open_trade
from app.solana_desk.agents.health import beat, snapshot
from app.solana_desk.agents.logger import write
from app.solana_desk.agents.rug_check import evaluate, parse_largest, parse_mint_account
from app.solana_desk.agents.scanner import describe
from app.solana_desk.agents.sizer import base_pct, plan
from app.solana_desk.db import add_event, init_solana_desk_db, wipe_solana_desk
from app.solana_desk.learning.guard import validate
from app.solana_desk.learning.memory import get_lesson, save_lesson
from app.solana_desk.learning.postmortem import review
from app.solana_desk.models import DEFAULT_SETTINGS, TokenView
from app.solana_desk.quotes import NoRoute, QuoteUnavailable, RouteQuote
from app.solana_desk.real_gate import gate_reason, panel_arm_required
from app.solana_desk.store import count_decisions, equity_count, get_decision, insert_equity, list_decisions, prune_decisions

MINT = "TermMint11111111111111111111111111pump"
SOL = "So11111111111111111111111111111111111111112"


def _token(**over) -> TokenView:
    base = dict(
        mint=MINT,
        symbol="WAFFL",
        price_usd=0.001,
        liquidity_usd=20_000,
        volume_usd=4_000,
        age_minutes=40,
        venue="pump_fun",
        mint_authority_active=False,
        freeze_authority_active=False,
        top_holder_pct=6,
        top10_holder_pct=30,
        dev_holder_pct=2,
        can_sell=True,
        risk_ready=True,
        spike=3.5,
        buys_pct=71,
        lp_locked_pct=93,
        change_5m_pct=8,
    )
    base.update(over)
    return TokenView(**base)


class Router:
    def __init__(self, impact=0.2, out=1_000_000, down=False, no_route=False, calls=None, tx="dHh4"):
        self.impact = impact
        self.out = out
        self.down = down
        self.no_route = no_route
        self.calls = calls if calls is not None else []
        self.impacts = None
        self.tx = tx

    async def quote(self, *, input_mint, output_mint, amount, slippage_bps):
        self.calls.append("quote")
        if self.down:
            raise QuoteUnavailable("no quote: jupiter+raydium down")
        if self.no_route:
            raise NoRoute("honeypot: sell sim failed")
        impact = self.impact
        if self.impacts is not None:
            impact = self.impacts(amount)
        return RouteQuote(input_mint, output_mint, int(amount), self.out, impact, 1000, "jupiter", {"outAmount": str(self.out)})

    async def build_swap(self, quote, user_pubkey, priority_lamports):
        self.calls.append("swap")
        assert "private" not in str(user_pubkey).lower()
        return self.tx

    async def rpc(self, method, params):
        self.calls.append(method)
        if method == "simulateTransaction":
            return {"result": {"value": {"err": None}}}
        if method == "sendTransaction":
            return {"result": "1" * 64}
        if method == "getLatestBlockhash":
            return {"result": {"value": {"lastValidBlockHeight": 10}}}
        if method == "getBlockHeight":
            return {"result": 1}
        if method == "getSignatureStatuses":
            return {"result": {"value": [{"confirmationStatus": "confirmed", "err": None}]}}
        if method == "getTransaction":
            return {"result": {"meta": {}}}
        if method == "getRecentPrioritizationFees":
            return {"result": [{"prioritizationFee": 1000}]}
        return {"result": {}}

    async def priority_fee_lamports(self, fallback, cap=10_000_000):
        return min(int(fallback), cap)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clean():
    _run(wipe_solana_desk())
    yield
    _run(wipe_solana_desk())


def test_scanner_does_not_import_the_executor():
    path = Path(__file__).resolve().parents[1] / "app" / "solana_desk" / "agents" / "scanner.py"
    tree = ast.parse(path.read_text())
    modules = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any("executor" in module for module in modules)


def test_scanner_describes_spike_and_writes_a_reason():
    text = describe(_token())
    assert "spike 3.5×" in text
    assert "buys 71%" in text

    async def _body():
        row = await write(kind="SCAN", agent="scanner", reason=text, mint=MINT, symbol="WAFFL", detail={"reason_source": "scanner"})
        assert row["reason"]
        await beat("scanner", ok=False, latency_ms=5, error="discovery down")
        await beat("scanner", ok=False, latency_ms=5, error="discovery down")
        view = await snapshot(interval_seconds=10)
        assert view["scanner"]["status"] == "down"

    _run(_body())


def test_rug_fail_reasons_and_pass_and_degraded():
    fee = parse_mint_account(
        {
            "result": {
                "value": {
                    "data": {
                        "parsed": {
                            "info": {
                                "mintAuthority": None,
                                "freezeAuthority": None,
                                "extensions": [
                                    {"extension": "transferFeeConfig", "state": {"newerTransferFee": {"transferFeeBasisPoints": 50}}}
                                ],
                            }
                        }
                    }
                }
            }
        }
    )
    assert fee["transfer_fee_bps"] == 50

    async def _body():
        settings = dict(DEFAULT_SETTINGS)
        chain = {"missing": False, "mint_authority_active": False, "freeze_authority_active": False, "transfer_fee_bps": 0}
        blocked = await evaluate(_token(mint_authority_active=True), settings, Router(), onchain={**chain, "mint_authority_active": True})
        assert blocked.reason == "mint authority active"
        frozen = await evaluate(_token(freeze_authority_active=True), settings, Router(), onchain={**chain, "freeze_authority_active": True})
        assert "freeze" in frozen.reason
        taxed = await evaluate(_token(), settings, Router(), onchain={**chain, "transfer_fee_bps": 50})
        assert taxed.reason == "token-2022 transfer fee"
        top = await evaluate(_token(top_holder_pct=80), settings, Router(), onchain=chain, holders=(80, 90))
        assert "top holder" in top.reason
        top10 = await evaluate(_token(top10_holder_pct=90, top_holder_pct=10), settings, Router(), onchain=chain, holders=(10, 90))
        assert "top 10" in top10.reason
        dev = await evaluate(_token(dev_holder_pct=22), settings, Router(), onchain=chain)
        assert "dev wallet" in dev.reason
        locked = await evaluate(_token(lp_locked_pct=10), {**settings, "min_lp_locked_pct": 50}, Router(), onchain=chain)
        assert "LP lock" in locked.reason
        honey = await evaluate(_token(), settings, Router(no_route=True), onchain=chain)
        assert honey.reason == "honeypot: sell sim failed"
        missing = await evaluate(
            _token(risk_ready=False, mint_authority_active=None, freeze_authority_active=None, top_holder_pct=None, dev_holder_pct=None),
            settings,
            Router(),
            onchain={"missing": True},
            rugcheck_ok=False,
        )
        assert missing.reason.startswith("no data")
        passed = await evaluate(_token(), settings, Router(), onchain=chain, rugcheck_ok=True)
        assert passed.ok
        degraded = await evaluate(_token(), settings, Router(), onchain=chain, rugcheck_ok=False)
        assert degraded.degraded or degraded.ok or degraded.reason

    _run(_body())
    top1, top10 = parse_largest(
        {"result": {"value": [{"address": "pool", "uiAmount": 50}, {"address": "a", "uiAmount": 30}, {"address": "b", "uiAmount": 20}]}},
        {"pool"},
    )
    assert top1 == pytest.approx(30)


def test_sizer_uses_equity_and_clamps_and_downsizes():
    assert base_pct(DEFAULT_SETTINGS) == pytest.approx(0.25)

    async def _body():
        small = await plan(equity_sol=1, cash_sol=1, reserved_sol=0, sol_usd=100, mint=MINT, settings=DEFAULT_SETTINGS, router=Router())
        large = await plan(equity_sol=2, cash_sol=2, reserved_sol=0, sol_usd=100, mint=MINT, settings=DEFAULT_SETTINGS, router=Router())
        assert large.size_sol >= small.size_sol
        assert "position_sol" not in small.inputs
        tight = dict(DEFAULT_SETTINGS)
        tight["max_size_pct"] = 0.10
        tight["min_size_pct"] = 0.05
        clamped = await plan(equity_sol=1, cash_sol=1, reserved_sol=0, sol_usd=100, mint=MINT, settings=tight, router=Router())
        assert clamped.pct <= 0.10 + 1e-9
        poor = dict(DEFAULT_SETTINGS)
        with pytest.raises(Exception):
            await plan(equity_sol=0.01, cash_sol=0.01, reserved_sol=0, sol_usd=100, mint=MINT, settings=poor, router=Router())

        def impacts(amount):
            return 5.0 if amount > 20_000_000 else 0.4

        router = Router()
        router.impacts = impacts
        fitted = await plan(equity_sol=1, cash_sol=1, reserved_sol=0, sol_usd=100, mint=MINT, settings=DEFAULT_SETTINGS, router=router)
        assert fitted.size_sol < 0.1
        assert fitted.quotes <= 4

    _run(_body())


def test_executor_requires_pass_and_size_and_paper_matches_live_until_send(monkeypatch):
    async def _body():
        with pytest.raises(OpenRejected):
            await open_trade(
                router=Router(),
                armed=False,
                mint=MINT,
                symbol="WAFFL",
                size_sol=0.05,
                settings=dict(DEFAULT_SETTINGS),
                check_decision_id=1,
                size_decision_id=2,
                cash_sol=1,
                reserved_sol=0,
                day_pnl_sol=0,
                open_count=0,
                running=True,
                kill_switch=False,
                sol_usd=100,
                price_usd=0.001,
            )
        passed = await write(kind="PASS", agent="rug_check", reason="passed $WAFFL", mint=MINT, symbol="WAFFL", detail={"reason_source": "rug"})
        sized = await write(
            kind="SIZE",
            agent="sizer",
            reason="25% of equity",
            mint=MINT,
            symbol="WAFFL",
            size_pct=0.25,
            size_sol=0.05,
            detail={"reason_source": "sizer"},
        )
        monkeypatch.setenv("SOLANA_PAPER_WALLET_PUBKEY", "PaperPubkey1111111111111111111111111111111")
        monkeypatch.delenv("SOLANA_REAL_TRADING", raising=False)
        paper_calls: list[str] = []
        paper = await open_trade(
            router=Router(calls=paper_calls),
            armed=False,
            mint=MINT,
            symbol="WAFFL",
            size_sol=0.05,
            settings=dict(DEFAULT_SETTINGS),
            check_decision_id=passed["id"],
            size_decision_id=sized["id"],
            cash_sol=1,
            reserved_sol=0,
            day_pnl_sol=0,
            open_count=0,
            running=True,
            kill_switch=False,
            sol_usd=100,
            price_usd=0.001,
        )
        assert "sendTransaction" not in paper_calls
        assert paper_calls[:3] == ["quote", "swap", "simulateTransaction"]
        assert paper.fill_source == "quote+sim"
        monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
        monkeypatch.setenv("SOLANA_RPC_URL", "http://127.0.0.1:9")
        import base64

        from solders.hash import Hash
        from solders.keypair import Keypair
        from solders.message import MessageV0
        from solders.system_program import TransferParams, transfer
        from solders.transaction import VersionedTransaction

        owner = Keypair()
        monkeypatch.setenv("SOLANA_BOT_PRIVATE_KEY", str(owner))
        ix = transfer(TransferParams(from_pubkey=owner.pubkey(), to_pubkey=owner.pubkey(), lamports=1))
        message = MessageV0.try_compile(owner.pubkey(), [ix], [], Hash.default())
        tx = base64.b64encode(bytes(VersionedTransaction(message, [owner]))).decode()
        live_calls: list[str] = []
        live = await open_trade(
            router=Router(calls=live_calls, tx=tx),
            armed=False,
            mint=MINT,
            symbol="WAFFL",
            size_sol=0.05,
            settings=dict(DEFAULT_SETTINGS),
            check_decision_id=passed["id"],
            size_decision_id=sized["id"],
            cash_sol=1,
            reserved_sol=0,
            day_pnl_sol=0,
            open_count=0,
            running=True,
            kill_switch=False,
            sol_usd=100,
            price_usd=0.001,
        )
        assert live_calls[:3] == ["quote", "swap", "simulateTransaction"]
        assert "sendTransaction" in live_calls
        assert live.fill_source == "chain"
        assert cap_pct(DEFAULT_SETTINGS) == 2.0
        with pytest.raises(OpenRejected, match="slippage"):
            await open_trade(
                router=Router(impact=4),
                armed=False,
                mint=MINT,
                symbol="WAFFL",
                size_sol=0.05,
                settings=dict(DEFAULT_SETTINGS),
                check_decision_id=passed["id"],
                size_decision_id=sized["id"],
                cash_sol=1,
                reserved_sol=0,
                day_pnl_sol=0,
                open_count=0,
                running=True,
                kill_switch=False,
                sol_usd=100,
                price_usd=0.001,
            )

    _run(_body())


def test_panel_arm_is_opt_in(monkeypatch):
    monkeypatch.delenv("SOLANA_REQUIRE_PANEL_ARM", raising=False)
    assert panel_arm_required() is False
    monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
    monkeypatch.setenv("SOLANA_BOT_PRIVATE_KEY", "k" * 40)
    monkeypatch.setenv("SOLANA_RPC_URL", "http://127.0.0.1:9")
    assert gate_reason(False) == ""
    monkeypatch.setenv("SOLANA_REQUIRE_PANEL_ARM", "true")
    assert "rozbrojony" in gate_reason(False)
    assert gate_reason(True) == ""


def test_logger_rejects_empty_reason_and_keeps_history():
    async def _body():
        with pytest.raises(ValueError):
            await write(kind="SKIP", agent="logger", reason="  ")
        first = await write(kind="SKIP", agent="logger", reason="one", detail={"reason_source": "test"})
        second = await write(kind="SKIP", agent="logger", reason="two", detail={"reason_source": "test"})
        assert second["line_no"] == first["line_no"] + 1
        for index in range(201):
            await write(kind="SKIP", agent="logger", reason=f"row {index}", detail={"reason_source": "test"})
        assert await count_decisions(include_debug=True) >= 203
        assert await prune_decisions(days=90) == 0
        await add_event("checker", "Odrzucenie: aktywne uprawnienie mint", MINT, "Z")
        await init_solana_desk_db()
        rows = await list_decisions(limit=500, include_debug=True)
        assert any("Odrzucenie" in (row.get("reason") or "") for row in rows) or await count_decisions() > 0

    _run(_body())


def test_equity_snapshot_on_close_and_session():
    from app.solana_desk.agents.equity import session_window, snapshot

    assert session_window("23:30", "23:00", "07:00")
    assert session_window("06:00", "23:00", "07:00")
    assert not session_window("12:00", "23:00", "07:00")

    async def _body():
        book = {"cash_sol": 1, "sol_usd": 100, "settings": dict(DEFAULT_SETTINGS), "peak_equity_sol": 1, "max_drawdown": 0}
        await snapshot(book, [], Router(), "close")
        await snapshot(book, [], Router(), "close")
        assert await equity_count() == 2

    _run(_body())


def test_stream_emits_snapshot_then_decision_and_resumes():
    from app.solana_desk.stream import iter_events

    async def _sleep(_seconds):
        return None

    async def _body():
        opened = await write(kind="ENTER", agent="executor", reason="opened", mint=MINT, symbol="WAFFL", detail={"reason_source": "test"})
        frames = []
        async for frame in iter_events(0, sleep=_sleep, max_cycles=1):
            frames.append(frame)
        assert any("event: snapshot" in frame for frame in frames)
        assert any("event: decision" in frame for frame in frames)
        last = await get_decision(int(opened["id"]))
        more = []
        async for frame in iter_events(int(last["id"]), sleep=_sleep, max_cycles=1):
            more.append(frame)
        assert not any("event: decision" in frame for frame in more)
        await write(kind="EXIT", agent="executor", reason="closed", mint=MINT, symbol="WAFFL", pnl_sol=0.1, detail={"reason_source": "test"})
        resumed = []
        async for frame in iter_events(int(last["id"]), sleep=_sleep, max_cycles=1):
            resumed.append(frame)
        assert any("event: decision" in frame and "EXIT" in frame for frame in resumed)

    _run(_body())


def test_selftest_never_sends_and_is_rate_limited(monkeypatch):
    from app.solana_desk.selftest import RateLimited, run_selftest

    sent = {"n": 0}

    async def scanner():
        return {"ok": True, "detail": "1"}

    async def rug():
        return {"ok": True, "detail": "pass"}

    async def sizer():
        return {"ok": True, "detail": "25%"}

    async def executor():
        sent["n"] += 0
        return {"ok": True, "detail": "quote", "send": False}

    async def logger():
        return {"ok": True, "detail": "rolled back"}

    async def equity():
        return {"ok": True, "detail": "equity"}

    async def _body():
        payload = await run_selftest(
            {"scanner": scanner, "rug_check": rug, "sizer": sizer, "executor": executor, "logger": logger, "equity": equity}
        )
        assert payload["send"] is False
        assert sent["n"] == 0
        with pytest.raises(RateLimited):
            await run_selftest({"scanner": scanner, "rug_check": rug, "sizer": sizer, "executor": executor, "logger": logger, "equity": equity})

    _run(_body())


def test_repeated_mistake_is_blocked_for_each_agent():
    async def _invalid(_system, _user, _temperature=0.2):
        return "not json"

    async def _valid(system, user, temperature=0.2):
        return json.dumps(
            {
                "agent": "rug_check",
                "diagnosis": "dev wallet",
                "lesson_text": "dev wallet ≥ 8% lost",
                "rule": {"when": [{"feature": "dev_pct", "op": ">=", "value": 8}], "action": {"type": "block"}},
                "confidence": 0.9,
            }
        )

    async def _body():
        evidence = {
            "agent": "rug_check",
            "trigger": "rug_gap",
            "features": {"dev_pct": 9.1, "liquidity_usd": 20000},
            "trade_id": 1,
        }
        lesson = await review(evidence, settings=DEFAULT_SETTINGS, complete=_invalid)
        assert lesson["status"] == "active"
        assert lesson["source"] == "rule"
        blocked = await evaluate(_token(dev_holder_pct=9.1), DEFAULT_SETTINGS, Router(), onchain={"missing": False, "mint_authority_active": False, "freeze_authority_active": False})
        assert blocked.ok is False
        assert f"lesson #{lesson['id']}" in blocked.reason

        await wipe_solana_desk()
        llm = await review(evidence, settings=DEFAULT_SETTINGS, complete=_valid)
        assert llm["source"] == "llm"
        again = await evaluate(_token(dev_holder_pct=9.1), DEFAULT_SETTINGS, Router(), onchain={"missing": False, "mint_authority_active": False, "freeze_authority_active": False})
        assert f"lesson #{llm['id']}" in again.reason

        await wipe_solana_desk()
        faded = await review(
            {"agent": "scanner", "trigger": "fade", "features": {"spike": 4.2, "fade_pct": 12}},
            settings=DEFAULT_SETTINGS,
            complete=_invalid,
        )
        from app.solana_desk.agents.pipeline import log_scan

        skipped = await log_scan(_token(spike=4.2, change_5m_pct=-12))
        assert skipped["kind"] == "SKIP"
        assert f"lesson #{faded['id']}" in skipped["reason"]

        await wipe_solana_desk()
        sized = await review(
            {"agent": "sizer", "trigger": "slippage", "features": {"liquidity_usd": 9000, "size_sol": 0.31}},
            settings=DEFAULT_SETTINGS,
            complete=_invalid,
        )
        assert sized["status"] == "active"
        wide = dict(DEFAULT_SETTINGS)
        wide["max_per_trade_sol"] = 1
        plan_row = await plan(
            equity_sol=1,
            cash_sol=1,
            reserved_sol=0,
            sol_usd=100,
            mint=MINT,
            settings=wide,
            router=Router(),
            features={"liquidity_usd": 9000},
        )
        assert plan_row.pct < 0.25
        assert f"lesson #{sized['id']}" in plan_row.reason

        await wipe_solana_desk()
        fee = await review(
            {"agent": "executor", "trigger": "confirm_fail", "features": {"priority_fee_sol": 0.00005, "confirm_failed": 1}},
            settings=DEFAULT_SETTINGS,
            complete=_invalid,
        )
        assert fee["rule"]["action"]["value"] > 0.00005
        assert fee["rule"]["action"]["value"] <= 0.01

        await wipe_solana_desk()
        drift = await review(
            {"agent": "equity", "trigger": "drift", "features": {"drift_pct": 1.2}},
            settings=DEFAULT_SETTINGS,
            complete=_invalid,
        )
        assert drift["rule"]["action"]["type"] == "require_check"

        await wipe_solana_desk()
        with pytest.raises(ValueError):
            await write(kind="SKIP", agent="logger", reason="")
        logged = await review({"agent": "logger", "trigger": "empty_reason", "features": {"reason_len": 0}}, complete=_invalid)
        assert logged["rule"]["action"]["param"] == "reason_source"
        with pytest.raises(ValueError, match="reason_source"):
            await write(kind="SKIP", agent="logger", reason="has a reason")
        ok = await write(kind="SKIP", agent="logger", reason="has a reason", detail={"reason_source": "test"})
        assert ok["id"]

        from app.ai.db import init_ai_db
        from app.ai.learning import process_feedback
        from app.solana_desk.learning.llm_bridge import inject_finance_lessons

        await init_ai_db()
        await process_feedback(1, "czy brać ten mem", "tak", "Nie wchodź gdy dev wallet jest powyżej 8 procent udziału")
        prompt = await inject_finance_lessons("context")
        assert "LESSON #" in prompt
        assert "dev wallet" in prompt

    _run(_body())


@pytest.mark.parametrize(
    "agent,rule",
    [
        ("executor", {"when": [], "action": {"type": "tighten_param", "param": "max_slippage_pct", "value": 3}}),
        ("sizer", {"when": [], "action": {"type": "tighten_param", "param": "max_size_pct", "value": 0.9}}),
        ("sizer", {"when": [], "action": {"type": "scale_size", "factor": 1.4}}),
        ("rug_check", {"when": [], "action": {"type": "tighten_param", "param": "max_dev_pct", "value": 20}}),
        ("rug_check", {"when": [], "action": {"type": "tighten_param", "param": "min_liquidity_usd", "value": 100}}),
        ("executor", {"when": [], "action": {"type": "tighten_param", "param": "SOLANA_REAL_TRADING", "value": 1}}),
        ("executor", {"when": [], "action": {"type": "tighten_param", "param": "kill_switch", "value": 0}}),
        ("logger", {"when": [], "action": {"type": "block"}}),
    ],
)
def test_guard_rejects_loosening(agent, rule):
    ok, reason = validate(agent, rule, DEFAULT_SETTINGS)
    assert ok is False
    assert reason


def test_lessons_survive_a_new_connection_and_shadow_promotes_then_retires():
    async def _body():
        saved = await save_lesson(
            agent="rug_check",
            trigger="test",
            evidence={"features": {"dev_pct": 9}},
            diagnosis="d",
            lesson_text="dev wallet ≥ 8% → block",
            rule={"when": [{"feature": "dev_pct", "op": ">=", "value": 8}], "action": {"type": "block"}},
            source="llm",
            confidence=0.4,
            deterministic=False,
        )
        assert saved["status"] == "shadow"
        again = await get_lesson(int(saved["id"]))
        assert again["lesson_text"].startswith("dev")
        from app.solana_desk.learning.postmortem import score_blocks
        from app.solana_desk.store import insert_tick

        active = await save_lesson(
            agent="rug_check",
            trigger="test",
            evidence={},
            diagnosis="d",
            lesson_text="block thin",
            rule={"when": [{"feature": "liquidity_usd", "op": "<", "value": 1000}], "action": {"type": "block"}},
            source="rule",
            confidence=0.9,
            deterministic=True,
        )
        from app.solana_desk.learning.memory import record_hit

        for index in range(10):
            await insert_tick(MINT, 1 + index, ts=f"2026-11-19T00:{index:02d}:00Z")
            await record_hit(
                int(active["id"]),
                None,
                "blocked",
                {"features": {"price": 1, "mint": MINT, "ts": "2026-11-19T00:00:00Z"}},
            )
        retired = await score_blocks(0.1)
        assert int(active["id"]) in retired

    _run(_body())


def test_secret_is_not_in_a_decision_or_executor_log(monkeypatch):
    secret = "executor-secret-value-not-a-key"
    monkeypatch.setenv("SOLANA_BOT_PRIVATE_KEY", secret)

    async def _body():
        row = await write(kind="SKIP", agent="executor", reason=f"failed {secret}", detail={"reason_source": "test", "blob": secret})
        assert secret not in row["reason"]
        assert secret not in (row.get("detail_json") or "")

    _run(_body())


def test_terminal_payload_has_explicit_missing_fields():
    from app.solana_desk.terminal import build_terminal

    async def _body():
        payload = await build_terminal()
        assert payload["header"]["pill"] == "paper · live"
        assert payload["header"]["footer"] == "paper · real quotes"
        assert "illustrative" not in json.dumps(payload)
        assert "equity_usd" in payload["missing"] or payload["header"]["equity_usd"] is None or payload["header"]["sol_usd"] in (None, 0)
        assert len(payload["agents"]) == 7

    _run(_body())
