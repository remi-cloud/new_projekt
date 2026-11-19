"""OpenAI-compatible LLM client.

Chain for provider xai and auto: xAI (if a key is set) → OpenAI (if a key is set)
→ llm7 only when external chat is enabled. Ollama is used only when the provider
is explicitly ollama. Keys stay in memory and are scrubbed from logs.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmTarget:
    base_url: str
    model: str
    api_key: str | None
    provider: str


def _provider_name() -> str:
    raw = (settings.ai_provider or "xai").strip().lower()
    if raw in {"auto", ""}:
        return "auto"
    return raw


def _secret_values() -> list[str]:
    values: list[str] = []
    for raw in (getattr(settings, "xai_api_key", ""), settings.openai_api_key):
        text = (raw or "").strip()
        if len(text) >= 4 and text not in values:
            values.append(text)
    return values


def redact_secrets(text: str) -> str:
    """Remove configured API keys from a string before it is logged or returned."""
    redacted = text or ""
    for secret in _secret_values():
        redacted = redacted.replace(secret, "[redacted]")
    return redacted


def _llm7_models() -> list[str]:
    primary = (settings.free_llm_model or "").strip()
    fallbacks = [
        part.strip()
        for part in (settings.free_llm_fallback_models or "").split(",")
        if part.strip()
    ]
    models: list[str] = []
    for name in [primary, *fallbacks]:
        if name and name not in models:
            models.append(name)
    return models or ["codestral-latest"]


def _xai_target() -> LlmTarget | None:
    key = (getattr(settings, "xai_api_key", "") or "").strip()
    if not key:
        return None
    base = (getattr(settings, "xai_base_url", "") or "https://api.x.ai/v1").strip().rstrip("/")
    model = (getattr(settings, "xai_model", "") or "grok-4").strip() or "grok-4"
    return LlmTarget(base or "https://api.x.ai/v1", model, key, "xai")


def _openai_target() -> LlmTarget | None:
    key = (settings.openai_api_key or "").strip()
    if not key:
        return None
    base = (settings.openai_base_url or "https://api.openai.com/v1").strip().rstrip("/")
    model = (settings.openai_model or "gpt-4o-mini").strip() or "gpt-4o-mini"
    return LlmTarget(base or "https://api.openai.com/v1", model, key, "openai")


def _llm7_targets() -> list[LlmTarget]:
    if not bool(getattr(settings, "ai_external_enabled", False)):
        return []
    base = (settings.free_llm_base_url or "https://api.llm7.io/v1").strip().rstrip("/")
    return [LlmTarget(base, model, None, "llm7") for model in _llm7_models()]


def _ollama_target() -> LlmTarget | None:
    ollama_base = (settings.ollama_base_url or "").strip().rstrip("/")
    ollama_model = (settings.ollama_model or "").strip()
    if not ollama_base or not ollama_model:
        return None
    return LlmTarget(ollama_base, ollama_model, None, "ollama")


def free_targets() -> list[LlmTarget]:
    """Keyless catalog (llm7 models, then Ollama when a URL is set).

    This is not the live request chain. llm7 is used only when external chat
    is enabled, and Ollama only when the provider is explicitly ollama.
    """
    base = (settings.free_llm_base_url or "https://api.llm7.io/v1").rstrip("/")
    targets = [LlmTarget(base, model, None, "llm7") for model in _llm7_models()]
    ollama = _ollama_target()
    if ollama:
        targets.append(ollama)
    return targets


def free_chain_labels() -> list[str]:
    """Labels for the UI. Empty when the first live target is a keyed provider."""
    targets = _targets_for_request()
    if not targets or targets[0].provider in {"xai", "openai"}:
        return []
    return [
        f"{target.provider}:{target.model}"
        for target in targets
        if target.provider not in {"xai", "openai"}
    ]


def _local_target(target: LlmTarget) -> bool:
    host = (urlparse(target.base_url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _keyed_chain() -> list[LlmTarget]:
    """xAI, then OpenAI, then llm7 when that opt-in is on. No implicit Ollama."""
    targets: list[LlmTarget] = []
    xai = _xai_target()
    if xai:
        targets.append(xai)
    openai = _openai_target()
    if openai:
        targets.append(openai)
    targets.extend(_llm7_targets())
    return targets


def _targets_for_request() -> list[LlmTarget]:
    provider = _provider_name()
    if provider == "openai":
        target = _openai_target()
        return [target] if target else []
    if provider == "llm7":
        return _llm7_targets()
    if provider == "ollama":
        target = _ollama_target()
        return [target] if target else []
    if provider in {"xai", "auto"}:
        return _keyed_chain()
    return []


def resolve_llm() -> tuple[str, str, str | None, str]:
    """Return the first target: (base_url, model, api_key_or_none, provider_id).

    An empty chain returns provider ``none`` instead of raising.
    """
    targets = _targets_for_request()
    if not targets:
        return "", "", None, "none"
    target = targets[0]
    return target.base_url, target.model, target.api_key, target.provider


def llm_provider() -> str:
    return resolve_llm()[3]


def active_llm_target() -> LlmTarget | None:
    targets = _targets_for_request()
    return targets[0] if targets else None


def llm_configured() -> bool:
    if not settings.ai_enabled:
        return False
    return bool(_targets_for_request())


async def llm_reachable(target: LlmTarget | None = None) -> bool:
    """True only after the configured endpoint answers. Ollama gets no auth header."""
    if target is None:
        targets = _targets_for_request()
        if not targets:
            return False
        target = targets[0]
    headers = {"Accept": "application/json"}
    if target.provider != "ollama" and target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    timeout = httpx.Timeout(1.5, connect=0.4)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{target.base_url.rstrip('/')}/models", headers=headers)
        return 200 <= response.status_code < 300
    except httpx.HTTPError:
        return False


def image_generation_configured() -> bool:
    return bool(
        settings.news_images_enabled
        and settings.news_images_use_dalle
        and settings.openai_api_key.strip()
    )


def _timeout_for(target: LlmTarget) -> httpx.Timeout:
    total = float(settings.ai_timeout_seconds)
    if target.provider == "ollama":
        # Local daemon is either up or not — don't stall the free chain on a dead port.
        return httpx.Timeout(min(total, 45.0), connect=2.0)
    return httpx.Timeout(total, connect=8.0)


async def _post_once(
    client: httpx.AsyncClient,
    target: LlmTarget,
    body: dict[str, Any],
    timeout: httpx.Timeout,
) -> httpx.Response:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if target.provider != "ollama" and target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    return await client.post(
        f"{target.base_url}/chat/completions",
        headers=headers,
        json=body,
        timeout=timeout,
    )


async def chat_completion(
    messages: list[dict[str, str]],
    tools: list[dict] | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    if not llm_configured():
        raise RuntimeError("LLM not configured")

    targets = _targets_for_request()
    temp = temperature if temperature is not None else settings.ai_temperature
    last_error = "LLM request failed"

    async with httpx.AsyncClient() as client:
        for target in targets:
            body: dict[str, Any] = {
                "model": target.model,
                "messages": messages,
                "temperature": temp,
            }
            use_tools = bool(tools)
            if use_tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"
            timeout = _timeout_for(target)
            try:
                resp = await _post_once(client, target, body, timeout)
                if resp.status_code >= 400 and use_tools and target.provider not in {"openai", "xai"}:
                    body.pop("tools", None)
                    body.pop("tool_choice", None)
                    logger.info(
                        "LLM %s/%s rejected tools (%s) — retrying without tools",
                        target.provider,
                        target.model,
                        resp.status_code,
                    )
                    resp = await _post_once(client, target, body, timeout)
            except httpx.HTTPError as exc:
                last_error = f"{target.provider}/{target.model} unreachable"
                logger.info("LLM %s: %s", redact_secrets(last_error), exc.__class__.__name__)
                continue

            if resp.status_code >= 400:
                last_error = f"{target.provider}/{target.model} HTTP {resp.status_code}"
                logger.info("LLM skipped: %s", redact_secrets(last_error))
                continue
            try:
                return resp.json()
            except ValueError:
                last_error = f"{target.provider}/{target.model} bad JSON"
                logger.info("LLM skipped: %s", redact_secrets(last_error))
                continue

    raise RuntimeError(last_error)


def extract_message(data: dict) -> dict[str, Any]:
    choice = data.get("choices", [{}])[0]
    return choice.get("message", {})


def parse_tool_calls(message: dict) -> list[dict]:
    return message.get("tool_calls") or []


def message_content(message: dict) -> str:
    return (message.get("content") or "").strip()


async def simple_complete(system: str, user: str, temperature: float = 0.3) -> str:
    data = await chat_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
    )
    return message_content(extract_message(data))


async def generate_image(prompt: str) -> bytes:
    """Generate image bytes via OpenAI Images API (DALL-E)."""
    if not image_generation_configured():
        raise RuntimeError("Image generation not configured")

    url = f"{settings.openai_base_url.rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": settings.openai_image_model,
        "prompt": prompt[:4000],
        "n": 1,
        "size": settings.openai_image_size,
        "response_format": "b64_json",
    }
    if settings.openai_image_model.startswith("dall-e-3"):
        body["quality"] = settings.openai_image_quality

    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    b64 = data["data"][0].get("b64_json")
    if not b64:
        raise RuntimeError("No image data in response")
    return base64.b64decode(b64)
