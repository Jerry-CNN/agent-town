"""WebSocket endpoint for Agent Town real-time communication.

Implements the Phase 4 WebSocket push protocol:
  - D-05: Send full snapshot on connect BEFORE adding client to broadcast list
    (prevents delta race condition — Pitfall 2 from 04-RESEARCH.md)
  - D-06: Broadcast agent_update, conversation, simulation_status, snapshot events
  - D-08: Handle pause/resume commands from browser
  - T-04-04: Invalid messages return type="error" and do not crash the endpoint
  - T-04-06: Dead connections removed during broadcast (in ConnectionManager)

Access to engine and connection_manager via websocket.app.state (set by lifespan).
The websocket.app accessor reaches the FastAPI application instance through the
ASGI scope, which is the correct pattern for WebSocket endpoints (Request injection
is HTTP-only in FastAPI's DI system).
"""
import time
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.schemas import WSMessage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint: snapshot on connect, pause/resume commands, ping/pong.

    Flow:
    1. Accept the raw WebSocket connection
    2. Get engine and connection_manager from websocket.app.state (set by lifespan)
    3. If engine is unavailable, send an error and close gracefully
    4. Send full snapshot BEFORE registering with connection_manager (D-05)
    5. Register with connection_manager (now receives future deltas)
    6. Enter receive loop: parse WSMessage, dispatch pause/resume/ping
    7. On disconnect: remove from connection_manager
    """
    await websocket.accept()

    # Access engine and manager via app.state (populated by lifespan).
    # websocket.app accesses the FastAPI application through the ASGI scope —
    # the correct pattern for WebSocket endpoints where Request injection is
    # not available through FastAPI's DI.
    app = websocket.app
    engine = getattr(app.state, "engine", None)
    manager = getattr(app.state, "connection_manager", None)

    # Graceful degradation: if engine not ready (startup race), send error and close
    if engine is None or manager is None:
        error_msg = WSMessage(
            type="error",
            payload={"detail": "Simulation not yet initialized — try again shortly"},
            timestamp=time.time(),
        )
        await websocket.send_text(error_msg.model_dump_json())
        await websocket.close()
        return

    # D-05: Send snapshot FIRST, then add to manager's active list.
    # This ensures the client receives full state before any broadcast deltas
    # arrive. If we registered first, a broadcast could arrive between
    # manager.connect() and the snapshot send, causing the client to see
    # a delta before the baseline state (Pitfall 2 mitigation).
    snapshot_data = engine.get_snapshot()
    snapshot_msg = WSMessage(
        type="snapshot",
        payload=snapshot_data,
        timestamp=time.time(),
    )
    await websocket.send_text(snapshot_msg.model_dump_json())

    # Now register: client will receive all future broadcast deltas
    manager.register(websocket)

    try:
        while True:
            text = await websocket.receive_text()
            try:
                message = WSMessage.model_validate_json(text)
            except Exception as exc:
                # T-04-04: Invalid messages return error without crashing
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

            elif message.type == "pause":
                # D-08: Pause command — halts simulation after current tick
                engine.pause()
                logger.info("Simulation paused via WebSocket command")
                # Broadcast simulation_status to all connected clients
                status_msg = WSMessage(
                    type="simulation_status",
                    payload={"status": "paused"},
                    timestamp=time.time(),
                )
                await manager.broadcast(status_msg.model_dump_json())

            elif message.type == "resume":
                # D-08: Resume command — restarts the paused simulation
                engine.resume()
                logger.info("Simulation resumed via WebSocket command")
                # Broadcast simulation_status to all connected clients
                status_msg = WSMessage(
                    type="simulation_status",
                    payload={"status": "running"},
                    timestamp=time.time(),
                )
                await manager.broadcast(status_msg.model_dump_json())

            elif message.type == "inject_event":
                # Phase 6: User-injected event — store in agent memory streams
                text = str(message.payload.get("text", "")).strip()
                mode = str(message.payload.get("mode", "broadcast"))
                target = message.payload.get("target")  # str | None
                if target is not None:
                    target = str(target)

                # T-06-01: Reject empty or whitespace-only event text
                if not text:
                    error_msg = WSMessage(
                        type="error",
                        payload={"detail": "Event text is empty"},
                        timestamp=time.time(),
                    )
                    await websocket.send_text(error_msg.model_dump_json())
                    continue

                # T-06-02: Validate mode is "broadcast" or "whisper"
                if mode not in ("broadcast", "whisper"):
                    error_msg = WSMessage(
                        type="error",
                        payload={"detail": f"Invalid mode: {mode}"},
                        timestamp=time.time(),
                    )
                    await websocket.send_text(error_msg.model_dump_json())
                    continue

                # Inject event into agent memory streams (await — uses asyncio.to_thread)
                await engine.inject_event(text=text, mode=mode, target=target)
                logger.info(
                    "Event injected: mode=%s target=%s text=%.80r",
                    mode, target, text,
                )

                # D-09: Broadcast event confirmation to activity feed for all clients
                if mode == "broadcast":
                    label = f"Event broadcast: {text}"
                else:
                    label = f"Whispered to {target}: {text}"
                event_msg = WSMessage(
                    type="event",
                    payload={"text": label},
                    timestamp=time.time(),
                )
                await manager.broadcast(event_msg.model_dump_json())

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        # Always clean up from active connections, even on unexpected errors
        manager.disconnect(websocket)
