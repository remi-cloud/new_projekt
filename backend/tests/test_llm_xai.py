"""xAI Grok is first when a key is set. No key is an honest local chat."""

import logging

import httpx
import pytest

from app.ai.llm import chat_completion, llm_configured, redact_secrets, resolve_llm
from app.config import Settings


def _clear_provider_env(monkeypatch):
    for name in (
        "CYCLICAL_AI_PROVIDER",
        "XAI_API_KEY",
        "CYCLICAL_XAI_API_KEY",
        "XAI_MODEL",
        "CYCLICAL_XAI_MODEL",
        "XAI_BASE_URL",
        "CYCLICAL_XAI_BASE_URL",
        "CYCLICAL_OPENAI_API_KEY",
        "CYCLICAL_AI_EXTERNAL",
        "CYCLICAL_AI_EXTERNAL_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)


def test_xai_key_accepts_both_env_names(monkeypatch, tmp_path):
    _clear_provider_env(monkeypatch)
    env = tmp_path / ".env"
    env.write_text("XAI_API_KEY=xai-from-bare\nXAI_MODEL=grok-4\n", encoding="utf-8")
    bare = Settings(_env_file=env)
    assert bare.xai_api_key == "xai-from-bare"
    assert bare.xai_model == "grok-4"
    assert bare.xai_base_url == "https://api.x.ai/v1"
    env.write_text(
        "CYCLICAL_XAI_API_KEY=xai-from-prefix\nXAI_API_KEY=xai-from-bare\n",
        encoding="utf-8",
    )
    both = Settings(_env_file=env)
    assert both.xai_api_key == "xai-from-prefix"


def test_default_provider_is_xai(monkeypatch, tmp_path):
    _clear_provider_env(monkeypatch)
    env = tmp_path / "empty.env"
    env.write_text("CYCLICAL_AI_ENABLED=true\n", encoding="utf-8")
    settings = Settings(_env_file=env)
    assert settings.ai_provider == "xai"


def test_chain_prefers_xai_then_openai(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "xai_api_key", "xai-secret")
    monkeypatch.setattr(settings, "xai_model", "grok-4")
    monkeypatch.setattr(settings, "xai_base_url", "https://api.x.ai/v1")
    monkeypatch.setattr(settings, "openai_api_key", "sk-openai")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "ai_external_enabled", False)
    base, model, key, provider = resolve_llm()
    assert provider == "xai"
    assert model == "grok-4"
    assert key == "xai-secret"
    assert base == "https://api.x.ai/v1"
    monkeypatch.setattr(settings, "xai_api_key", "")
    assert resolve_llm()[3] == "openai"


def test_status_without_a_key_is_honest(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "xai")
    monkeypatch.setattr(settings, "xai_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "ai_external_enabled", False)
    status = client.get("/api/ai/status")
    assert status.status_code == 200
    body = status.json()
    assert body["llm_configured"] is False
    assert body["provider"] == "none"
    assert body["requires_api_key"] is True
    assert body["model"] == ""


def test_status_hides_the_key(client, monkeypatch):
    from app.config import settings

    secret = "xai-super-secret-value"
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "xai")
    monkeypatch.setattr(settings, "xai_api_key", secret)
    monkeypatch.setattr(settings, "xai_model", "grok-4")
    monkeypatch.setattr(settings, "xai_base_url", "https://api.x.ai/v1")
    monkeypatch.setattr(settings, "openai_api_key", "")
    status = client.get("/api/ai/status")
    assert status.status_code == 200
    body = status.json()
    assert body["provider"] == "xai"
    assert body["model"] == "grok-4"
    assert body["llm_configured"] is True
    assert body["requires_api_key"] is False
    assert secret not in status.text
    assert redact_secrets(f"token {secret}") == "token [redacted]"


def test_disabled_ai_is_503(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", False)
    response = client.post("/api/ai/chat", json={"message": "Jaki jest trend BTC-USD?", "symbol": "BTC-USD"})
    assert response.status_code == 503
    assert "CYCLICAL_AI_ENABLED" in response.json()["detail"]


def test_guest_analyze_stays_on_the_desk(client):
    client.cookies.clear()
    response = client.post("/api/ai/analyze/BTC-USD", headers={"X-Desk-Token": ""})
    assert response.status_code == 401


def test_external_alias(monkeypatch, tmp_path):
    _clear_provider_env(monkeypatch)
    env = tmp_path / ".env"
    env.write_text("CYCLICAL_AI_EXTERNAL=true\n", encoding="utf-8")
    assert Settings(_env_file=env).ai_external_enabled is True


class _Resp:
    def __init__(self, code: int, payload: dict | None = None):
        self.status_code = code
        self._payload = payload or {"choices": [{"message": {"content": "ok"}}]}

    def json(self):
        return self._payload


class _Scripted:
    calls: list[str] = []
    script: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None, timeout=None):
        _Scripted.calls.append(url)
        step = _Scripted.script.pop(0)
        if step == "connect":
            raise httpx.ConnectError("down")
        code, payload = step
        return _Resp(code, payload)


@pytest.mark.asyncio
async def test_chat_walks_xai_then_openai(monkeypatch, caplog):
    from app.config import settings

    secret = "xai-walk-secret"
    openai_secret = "sk-walk-openai"
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "xai")
    monkeypatch.setattr(settings, "xai_api_key", secret)
    monkeypatch.setattr(settings, "xai_model", "grok-4")
    monkeypatch.setattr(settings, "xai_base_url", "https://api.x.ai/v1")
    monkeypatch.setattr(settings, "openai_api_key", openai_secret)
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "ai_external_enabled", False)
    _Scripted.calls = []
    _Scripted.script = ["connect", (200, {"choices": [{"message": {"content": "dalej"}}]})]
    monkeypatch.setattr("app.ai.llm.httpx.AsyncClient", _Scripted)
    with caplog.at_level(logging.INFO):
        data = await chat_completion(
            [{"role": "user", "content": "hi"}],
            tools=[{"type": "function", "function": {"name": "analyze_trend"}}],
        )
    assert data["choices"][0]["message"]["content"] == "dalej"
    assert _Scripted.calls[0].startswith("https://api.x.ai/")
    assert any(url.startswith("https://api.openai.com/") for url in _Scripted.calls)
    assert secret not in caplog.text
    assert openai_secret not in caplog.text
    assert llm_configured() is True
