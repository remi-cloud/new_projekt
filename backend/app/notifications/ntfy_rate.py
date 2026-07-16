"""Shared ntfy.sh rate limiting — avoids 429 on free tier."""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

MAX_NTFY_PER_BATCH = 3
NTFY_DELAY_SEC = 0.6


async def post_ntfy(
    client: httpx.AsyncClient,
    *,
    topic: str,
    body: bytes,
    headers: dict[str, str],
) -> tuple[bool, bool]:
    """Post one ntfy message. Returns (success, rate_limited)."""
    try:
        resp = await client.post(f"https://ntfy.sh/{topic}", content=body, headers=headers)
        if resp.status_code == 429:
            logger.warning("ntfy rate limited (429) — stopping batch")
            return False, True
        if resp.is_success:
            return True, False
        logger.warning("ntfy failed %s: %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        logger.warning("ntfy error: %s", exc)
    return False, False


async def send_ntfy_batch(
    client: httpx.AsyncClient,
    *,
    topic: str,
    messages: list[tuple[bytes, dict[str, str]]],
    max_per_batch: int = MAX_NTFY_PER_BATCH,
) -> int:
    """Send up to max_per_batch messages with delay; stop on 429."""
    sent = 0
    for i, (body, headers) in enumerate(messages):
        if i >= max_per_batch:
            logger.info("ntfy batch capped at %d messages", max_per_batch)
            break
        ok, limited = await post_ntfy(client, topic=topic, body=body, headers=headers)
        if limited:
            break
        if ok:
            sent += 1
        if i < len(messages) - 1:
            await asyncio.sleep(NTFY_DELAY_SEC)
    return sent
