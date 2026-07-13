"""Broadcast live price/signal updates to WebSocket and SSE clients."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class LiveBroadcaster:
    def __init__(self) -> None:
        self._ws_clients: set[WebSocket] = set()
        self._sse_queues: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()
        self.last_event_at: datetime | None = None

    async def connect_ws(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._ws_clients.add(ws)

    async def disconnect_ws(self, ws: WebSocket) -> None:
        async with self._lock:
            self._ws_clients.discard(ws)

    def connect_sse(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
        self._sse_queues.add(q)
        return q

    def disconnect_sse(self, q: asyncio.Queue[str]) -> None:
        self._sse_queues.discard(q)

    async def publish(self, event_type: str, data: Any) -> None:
        payload = json.dumps(
            {
                "type": event_type,
                "data": data,
                "at": datetime.now(timezone.utc).isoformat(),
            },
            default=str,
        )
        self.last_event_at = datetime.now(timezone.utc)

        dead_ws: list[WebSocket] = []
        async with self._lock:
            for ws in self._ws_clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead_ws.append(ws)
            for ws in dead_ws:
                self._ws_clients.discard(ws)

        dead_sse: list[asyncio.Queue[str]] = []
        for q in list(self._sse_queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_sse.append(q)
        for q in dead_sse:
            self._sse_queues.discard(q)

    @property
    def client_count(self) -> int:
        return len(self._ws_clients) + len(self._sse_queues)


broadcaster = LiveBroadcaster()
