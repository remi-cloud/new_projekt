import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.realtime.broadcaster import broadcaster
from app.scanners.opportunity_scanner import scanner

router = APIRouter(tags=["live"])


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await broadcaster.connect_ws(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.disconnect_ws(ws)


@router.get("/api/live/stream")
async def live_stream():
    async def event_generator():
        queue = broadcaster.connect_sse()
        try:
            yield f"data: {json.dumps({'type': 'connected', 'live_mode': scanner.live_mode})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            broadcaster.disconnect_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
