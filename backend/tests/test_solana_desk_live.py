"""Real swaps: mocked Jupiter and RPC. No network and no funded key."""

import base64

import pytest
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

from app.solana_desk.db import disarm, read_armed, write_armed
from app.solana_desk.live import execute_swap
from app.solana_desk.models import DEFAULT_SETTINGS
from app.solana_desk.real_gate import KEY, RealTradingLocked
from app.solana_desk.risk import assess_risk

MINT = "LiveMint111111111111111111111111111pump"
SIG = "1" * 64


def _settings():
    return dict(DEFAULT_SETTINGS)


def _tx(owner: Keypair) -> str:
    ix = transfer(TransferParams(from_pubkey=owner.pubkey(), to_pubkey=owner.pubkey(), lamports=1))
    message = MessageV0.try_compile(owner.pubkey(), [ix], [], Hash.default())
    signed = VersionedTransaction(message, [owner])
    return base64.b64encode(bytes(signed)).decode()


class Fake:
    def __init__(self, tx: str, balance: int = 2_000_000_000, sim_err=None, confirm: bool = True):
        self.tx = tx
        self.balance = balance
        self.sim_err = sim_err
        self.confirm = confirm
        self.calls: list[str] = []

    async def jupiter_quote(self, params):
        self.calls.append("quote")
        return {"inAmount": params["amount"], "outAmount": "1000000", "slippageBps": params["slippageBps"]}

    async def jupiter_swap(self, body):
        self.calls.append("swap")
        assert "private" not in str(body).lower()
        return {"swapTransaction": self.tx}

    async def rpc(self, method, params):
        self.calls.append(method)
        if method == "getBalance":
            return {"result": {"value": self.balance}}
        if method == "simulateTransaction":
            return {"result": {"value": {"err": self.sim_err}}}
        if method == "sendTransaction":
            return {"result": SIG}
        if method == "getSignatureStatuses":
            if not self.confirm:
                return {"result": {"value": [None]}}
            return {"result": {"value": [{"confirmationStatus": "confirmed", "err": None}]}}
        raise AssertionError(method)


def _kw(**extra):
    base = dict(
        side="buy",
        mint=MINT,
        amount_sol=0.05,
        token_atoms=None,
        sol_usd=100,
        price_usd=0.001,
        slippage_bps=50,
        priority_fee_sol=0.00005,
        reserve_sol=0.05,
        cash_sol=1,
        reserved_sol=0,
        day_pnl_sol=0,
        open_count=0,
        running=True,
        kill_switch=False,
        settings=_settings(),
        pause=lambda _seconds: _async_none(),
    )
    base.update(extra)
    return base


async def _async_none():
    return None


def _open(monkeypatch, owner: Keypair):
    monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
    monkeypatch.setenv(KEY, str(owner))
    monkeypatch.setenv("SOLANA_RPC_URL", "http://127.0.0.1:9")


@pytest.mark.asyncio
async def test_closed_gates_never_touch_the_transport():
    fake = Fake(_tx(Keypair()))
    with pytest.raises(RealTradingLocked):
        await execute_swap(armed=False, transport=fake, **_kw())
    assert fake.calls == []


@pytest.mark.asyncio
async def test_flag_and_key_without_arm_or_rpc_do_not_send(monkeypatch):
    owner = Keypair()
    monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
    monkeypatch.setenv(KEY, str(owner))
    monkeypatch.delenv("SOLANA_RPC_URL", raising=False)
    fake = Fake(_tx(owner))
    with pytest.raises(RealTradingLocked):
        await execute_swap(armed=True, transport=fake, **_kw())
    assert fake.calls == []


@pytest.mark.asyncio
async def test_invalid_key_is_redacted_and_not_sent(monkeypatch):
    secret = "paper-only-secret-value-not-a-key"
    monkeypatch.setenv("SOLANA_REAL_TRADING", "true")
    monkeypatch.setenv(KEY, secret)
    monkeypatch.setenv("SOLANA_RPC_URL", "http://127.0.0.1:9")
    fake = Fake(_tx(Keypair()))

    class Boom(Fake):
        async def rpc(self, method, params):
            raise RuntimeError(secret)

    boom = Boom(fake.tx)
    with pytest.raises(RealTradingLocked) as caught:
        await execute_swap(armed=True, transport=boom, **_kw())
    assert secret not in str(caught.value)
    assert boom.calls == []


@pytest.mark.asyncio
async def test_caps_kill_and_reserve_abort_before_a_swap(monkeypatch):
    owner = Keypair()
    _open(monkeypatch, owner)
    fake = Fake(_tx(owner), balance=80_000_000)
    with pytest.raises(RealTradingLocked, match="poślizgu"):
        await execute_swap(armed=True, transport=fake, **_kw(slippage_bps=250))
    assert fake.calls == []
    with pytest.raises(RealTradingLocked, match="priorytetowej"):
        await execute_swap(armed=True, transport=fake, **_kw(priority_fee_sol=0.02))
    assert fake.calls == []
    with pytest.raises(RealTradingLocked, match="wyłącznik"):
        await execute_swap(armed=True, transport=fake, **_kw(kill_switch=True))
    assert fake.calls == []
    with pytest.raises(RealTradingLocked, match="rezerwa"):
        await execute_swap(armed=True, transport=fake, **_kw())
    assert "quote" not in fake.calls
    assert "sendTransaction" not in fake.calls


@pytest.mark.asyncio
async def test_failed_simulation_does_not_send(monkeypatch):
    owner = Keypair()
    _open(monkeypatch, owner)
    fake = Fake(_tx(owner), sim_err={"InstructionError": [0, "Custom"]})
    with pytest.raises(RealTradingLocked, match="Symulacja"):
        await execute_swap(armed=True, transport=fake, **_kw())
    assert "simulateTransaction" in fake.calls
    assert "sendTransaction" not in fake.calls


@pytest.mark.asyncio
async def test_build_sign_send_confirm_records_solscan(monkeypatch):
    owner = Keypair()
    _open(monkeypatch, owner)
    fake = Fake(_tx(owner))
    result = await execute_swap(armed=True, transport=fake, **_kw())
    assert result.signature == SIG
    assert result.solscan_url == f"https://solscan.io/tx/{SIG}"
    assert fake.calls.index("simulateTransaction") < fake.calls.index("sendTransaction")
    assert result.debit_sol > 0
    assert str(owner) not in result.solscan_url


@pytest.mark.asyncio
async def test_transport_error_redacts_the_key(monkeypatch):
    owner = Keypair()
    secret = str(owner)
    _open(monkeypatch, owner)
    fake = Fake(_tx(owner))

    async def explode(method, params):
        fake.calls.append(method)
        raise RuntimeError(f"rpc said {secret}")

    fake.rpc = explode
    with pytest.raises(RealTradingLocked) as caught:
        await execute_swap(armed=True, transport=fake, **_kw())
    assert secret not in str(caught.value)
    assert "[redacted]" in str(caught.value)


@pytest.mark.asyncio
async def test_arm_switch_resets():
    await disarm()
    await write_armed(True)
    assert await read_armed() is True
    await disarm()
    assert await read_armed() is False


def test_checker_still_rejects_before_a_real_send():
    from app.solana_desk.models import TokenView

    token = TokenView(
        mint=MINT,
        symbol="X",
        price_usd=0.001,
        liquidity_usd=8000,
        volume_usd=2000,
        age_minutes=30,
        venue="pump_fun",
        mint_authority_active=True,
        freeze_authority_active=False,
        top_holder_pct=4,
        top10_holder_pct=20,
        dev_holder_pct=1,
        can_sell=True,
        risk_ready=True,
    )
    assert assess_risk(token, DEFAULT_SETTINGS).ok is False


@pytest.mark.asyncio
async def test_confirmation_waits_between_polls_and_then_accepts():
    from app.solana_desk.live import _confirmed

    waits: list[float] = []

    async def pause(seconds: float) -> None:
        waits.append(seconds)

    class Client:
        def __init__(self) -> None:
            self.seen = 0

        async def rpc(self, method, params):
            assert method == "getSignatureStatuses"
            self.seen += 1
            if self.seen < 3:
                return {"result": {"value": [None]}}
            return {"result": {"value": [{"confirmationStatus": "confirmed", "err": None}]}}

    assert await _confirmed(Client(), "sig", pause) is True
    assert waits == [0.5, 0.5]


@pytest.mark.asyncio
async def test_confirmation_timeout_is_not_a_single_instant_poll():
    from app.solana_desk.live import _CONFIRM_POLLS, _confirmed

    waits: list[float] = []

    async def pause(seconds: float) -> None:
        waits.append(seconds)

    class Client:
        async def rpc(self, method, params):
            return {"result": {"value": [None]}}

    assert await _confirmed(Client(), "sig", pause) is False
    assert len(waits) == _CONFIRM_POLLS
    assert set(waits) == {0.5}


def test_arm_api_is_desk_only_and_does_not_activate_real(client):
    status = client.get("/api/solana/status")
    assert status.status_code == 200
    assert status.json()["armed"] is False
    assert status.json()["real_trading_active"] is False
    blocked = client.post("/api/solana/arm", json={"armed": True}, headers={"X-Desk-Token": ""})
    assert blocked.status_code == 401
    armed = client.post("/api/solana/arm", json={"armed": True})
    assert armed.status_code == 200
    body = armed.json()
    assert body["armed"] is True
    assert body["real_trading_active"] is False
    assert "private" not in armed.text.lower()
    client.post("/api/solana/arm", json={"armed": False})
