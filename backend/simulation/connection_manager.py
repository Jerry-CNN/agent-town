"""ConnectionManager — multi-client WebSocket broadcast for Agent Town.

Manages the list of active WebSocket connections and provides a broadcast
method that silently removes dead connections (T-04-06 mitigation).

Design decisions:
  - D-04: Push all state changes to all connected browser clients
  - D-05: Full snapshot sent to client before adding to active list (handled in ws.py)
  - T-04-06: Dead connections caught per-connection in try/except; removed after
    broadcast loop completes (never mutate list during iteration)
"""

from __future__ import annotations

import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages to all.

    Thread-safety note: this implementation is single-event-loop safe.
    All WebSocket operations (send_text, connect, disconnect) must be called
    from the same asyncio event loop as FastAPI.

    Usage:
        manager = ConnectionManager()

        # On client connect (send snapshot FIRST, then register):
        await websocket.accept()
        snapshot_msg = ...
        await websocket.send_text(snapshot_msg)
        manager.active_connections.append(websocket)

        # On broadcast:
        await manager.broadcast(msg_json)

        # On disconnect:
        manager.disconnect(websocket)
    """

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    def register(self, websocket: WebSocket) -> None:
        """Add an already-accepted WebSocket to the active broadcast list.

        Callers (ws.py) are responsible for accepting the connection and
        sending the full snapshot BEFORE registering.  This enforces the
        snapshot-first pattern (D-05): the client receives the baseline state
        before any broadcast deltas can arrive.

        The former connect() method (which called websocket.accept() internally)
        was removed because ws.py never used it — it accepted directly and then
        appended to active_connections, making connect() dead code that could
        trigger a double-accept RuntimeError if called by accident (WR-01).

        Args:
            websocket: An already-accepted WebSocket to add to the broadcast list.
        """
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active connections list.

        Safe to call even if the websocket is not in the list.

        Args:
            websocket: The WebSocket to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """Send a text message to all active connections.

        Dead connections (those that raise any exception on send_text) are
        collected and removed after the broadcast loop completes — never
        during iteration (T-04-06). The loop continues to all remaining
        connections even if some fail.

        Args:
            message: JSON-serialized string to send to all clients.
        """
        dead: list[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                # T-04-06: Log the dead connection and mark for removal.
                # Do NOT raise — other connections must still receive the message.
                logger.debug("Dead WebSocket connection detected during broadcast — removing")
                dead.append(ws)

        # Remove dead connections after full iteration (never mutate during loop)
        for ws in dead:
            self.active_connections.remove(ws)
