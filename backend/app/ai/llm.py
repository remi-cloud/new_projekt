"""OpenAI-compatible LLM client — paid OpenAI or free keyless providers (LLM7 / Ollama)."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _provider_name() -> str:
    raw = (settings.ai_provider or "auto").strip().lower()
    if raw in {"auto", ""}:
        return "openai" if settings.openai_api_key.strip() else "llm7"
    return raw


def resolve_llm() -> tuple[str, str, str | None, str]:
    """Return (base_url, model, api_key_or_none, provider_id)."""
    provider = _provider_name()
    if provider == "openai":
        key = settings.openai_api_key.strip() or None
        return (
            settings.openai_base_url.rstrip("/"),
            settings.openai_model,
            key,
            "openai",
        )
    if provider == "ollama":
        return (
            settings.ollama_base_url.rstrip("/"),
            settings.ollama_model,
            "ollama",  # Ollama accepts any/non-empty bearer; some builds ignore it
            "ollama",
        )
    # Default free keyless: LLM7 OpenAI-compatible gateway
    return (
        settings.free_llm_base_url.rstrip("/"),
        settings.free_llm_model,
        None,
        "llm7",
    )


def llm_provider() -> str:
    return resolve_llm()[3]


def llm_configured() -> bool:
    if not settings.ai_enabled:
        return False
    provider = _provider_name()
    if provider == "openai":
        return bool(settings.openai_api_key.strip())
    # llm7 / ollama — no API key required
    return True


def image_generation_configured() -> bool:
    return bool(
        settings.news_images_enabled
        and settings.news_images_use_dalle
        and settings.openai_api_key.strip()
    )


async def chat_completion(
    messages: list[dict[str, str]],
    tools: list[dict] | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    if not llm_configured():
        raise RuntimeError("LLM not configured")

    base_url, model, api_key, provider = resolve_llm()
    temp = temperature if temperature is not None else settings.ai_temperature
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temp,
    }
    if tools:
        # Free gateways may reject tools — try with tools first, caller handles errors
        body["tools"] = tools
        body["tool_choice"] = "auto"

    url = f"{base_url}/chat/completions"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = settings.ai_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code >= 400 and tools and provider != "openai":
            # Retry without tools on free providers that reject tool schemas
            body.pop("tools", None)
            body.pop("tool_choice", None)
            logger.info("LLM %s rejected tools (%s) — retrying without tools", provider, resp.status_code)
            resp = await client.post(url, headers=headers, json=body)
        if resp.status_code >= 400 and provider == "llm7":
            fallbacks = [
                m.strip()
                for m in (settings.free_llm_fallback_models or "").split(",")
                if m.strip() and m.strip() != model
            ]
            for alt in fallbacks:
                body["model"] = alt
                body.pop("tools", None)
                body.pop("tool_choice", None)
                logger.info("LLM7 fallback → %s", alt)
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code < 400:
                    break
        resp.raise_for_status()
        return resp.json()


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
