"""OpenAI-compatible LLM client — paid OpenAI or a free chain (LLM7 models, then Ollama)."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

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
    raw = (settings.ai_provider or "auto").strip().lower()
    if raw in {"auto", ""}:
        return "openai" if settings.openai_api_key.strip() else "llm7"
    return raw


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


def free_targets() -> list[LlmTarget]:
    """Every keyless provider, in the order the free mode should try them."""
    base = (settings.free_llm_base_url or "https://api.llm7.io/v1").rstrip("/")
    targets = [LlmTarget(base, model, None, "llm7") for model in _llm7_models()]
    ollama_base = (settings.ollama_base_url or "").strip().rstrip("/")
    ollama_model = (settings.ollama_model or "").strip()
    if ollama_base and ollama_model:
        targets.append(LlmTarget(ollama_base, ollama_model, "ollama", "ollama"))
    return targets


def free_chain_labels() -> list[str]:
    """Labels for the UI. Empty when a paid OpenAI key is the active provider."""
    if _provider_name() == "openai" and settings.openai_api_key.strip():
        return []
    return [f"{target.provider}:{target.model}" for target in free_targets()]


def _targets_for_request() -> list[LlmTarget]:
    provider = _provider_name()
    if provider == "openai":
        key = settings.openai_api_key.strip() or None
        return [
            LlmTarget(
                settings.openai_base_url.rstrip("/"),
                settings.openai_model,
                key,
                "openai",
            )
        ]
    chain = free_targets()
    if provider == "ollama":
        local = [target for target in chain if target.provider == "ollama"]
        remote = [target for target in chain if target.provider != "ollama"]
        return local + remote
    return chain


def resolve_llm() -> tuple[str, str, str | None, str]:
    """Return the first target: (base_url, model, api_key_or_none, provider_id)."""
    target = _targets_for_request()[0]
    return target.base_url, target.model, target.api_key, target.provider


def llm_provider() -> str:
    return resolve_llm()[3]


def llm_configured() -> bool:
    if not settings.ai_enabled:
        return False
    provider = _provider_name()
    if provider == "openai":
        return bool(settings.openai_api_key.strip())
    return bool(free_targets())


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
    if target.api_key:
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
                if resp.status_code >= 400 and use_tools and target.provider != "openai":
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
                logger.info("LLM %s: %s", last_error, exc.__class__.__name__)
                continue

            if resp.status_code >= 400:
                last_error = f"{target.provider}/{target.model} HTTP {resp.status_code}"
                logger.info("LLM skipped: %s", last_error)
                continue
            try:
                return resp.json()
            except ValueError:
                last_error = f"{target.provider}/{target.model} bad JSON"
                logger.info("LLM skipped: %s", last_error)
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
