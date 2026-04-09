"""WebSocket endpoint for Agent Town real-time communication (stub for Phase 4)."""
import time
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.schemas import WSMessage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint. Accepts connection, handles ping/pong, loops until disconnect."""
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            try:
                message = WSMessage.model_validate_json(text)
            except Exception as exc:
                logger.warning("Invalid WebSocket message: %s", exc)
                error_msg = WSMessage(
                    type="error",
                    payload={"detail": "Invalid message format"},
                    timestamp=time.time(),
                )
                await websocket.send_text(error_msg.model_dump_json())
                continue

            if message.type == "ping":
                pong = WSMessage(type="pong", payload={}, timestamp=time.time())
                await websocket.send_text(pong.model_dump_json())
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
