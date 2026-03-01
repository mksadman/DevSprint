import asyncio
import logging
from typing import List

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_active_connections: List[WebSocket] = []
_total_messages_sent: int = 0


def get_active_connection_count() -> int:
    return len(_active_connections)


def get_total_messages_sent() -> int:
    return _total_messages_sent


async def connect(websocket: WebSocket) -> None:
    """Accept and register a new WebSocket connection."""
    await websocket.accept()
    _active_connections.append(websocket)
    logger.info("WebSocket connected. Active connections: %d", len(_active_connections))


def disconnect(websocket: WebSocket) -> None:
    """Remove a WebSocket connection from the active pool."""
    if websocket in _active_connections:
        _active_connections.remove(websocket)
    logger.info("WebSocket disconnected. Active connections: %d", len(_active_connections))


async def send_personal_message(websocket: WebSocket, message: str) -> None:
    """Send a text message to a single WebSocket client."""
    global _total_messages_sent
    await websocket.send_text(message)
    _total_messages_sent += 1


async def broadcast(message: str) -> None:
    """Broadcast a text message to all active WebSocket clients."""
    global _total_messages_sent
    disconnected = []
    for connection in list(_active_connections):
        try:
            await connection.send_text(message)
            _total_messages_sent += 1
        except Exception as exc:
            logger.warning("Failed to send to a connection: %s", exc)
            disconnected.append(connection)
    for conn in disconnected:
        disconnect(conn)
