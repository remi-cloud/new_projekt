from app.ai.llm import llm_configured, llm_provider, resolve_llm


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


def test_openai_requires_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert llm_configured() is False
