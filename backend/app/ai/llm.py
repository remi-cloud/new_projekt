"""OpenAI-compatible LLM client."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def llm_configured() -> bool:
    return bool(settings.ai_enabled and settings.openai_api_key.strip())


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

    temp = temperature if temperature is not None else settings.ai_temperature
    body: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temp,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        resp = await client.post(url, headers=headers, json=body)
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
