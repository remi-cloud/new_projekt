import pytest

from app.ai.llm import chat_completion, extract_message, free_targets, llm_configured, llm_provider, resolve_llm


def test_auto_uses_llm7_without_openai_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert llm_configured() is True
    assert llm_provider() == "llm7"
    base, model, key, provider = resolve_llm()
    assert provider == "llm7"
    assert key is None
    assert "llm7.io" in base
    assert model


def test_free_chain_lists_llm7_models_then_ollama(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "free_llm_model", "codestral-latest")
    monkeypatch.setattr(settings, "free_llm_fallback_models", "meta-Llama-3.1-8B-Instruct-Turbo,minimax-m2.7")
    monkeypatch.setattr(settings, "ollama_base_url", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr(settings, "ollama_model", "llama3.2")
    labels = [(t.provider, t.model) for t in free_targets()]
    assert labels[0] == ("llm7", "codestral-latest")
    assert ("llm7", "minimax-m2.7") in labels
    assert labels[-1] == ("ollama", "llama3.2")


class _Resp:
    def __init__(self, code: int, payload: dict | None = None):
        self.status_code = code
        self._payload = payload or {"choices": [{"message": {"content": "ok"}}]}

    def json(self):
        return self._payload


class _Client:
    calls: list[str] = []
    script: list[tuple[int, dict | None]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None, timeout=None):
        _Client.calls.append(json["model"])
        code, payload = _Client.script.pop(0)
        return _Resp(code, payload)


@pytest.mark.asyncio
async def test_free_chat_uses_next_model_when_needed(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "llm7")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "free_llm_model", "primary-model")
    monkeypatch.setattr(settings, "free_llm_fallback_models", "second-model")
    monkeypatch.setattr(settings, "ollama_base_url", "")
    monkeypatch.setattr(settings, "ollama_model", "")
    _Client.calls = []
    _Client.script = [
        (503, None),
        (200, {"choices": [{"message": {"content": "dalej"}}]}),
    ]
    monkeypatch.setattr("app.ai.llm.httpx.AsyncClient", _Client)
    data = await chat_completion([{"role": "user", "content": "hi"}])
    assert extract_message(data)["content"] == "dalej"
    assert _Client.calls == ["primary-model", "second-model"]


def test_openai_requires_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert llm_configured() is False
