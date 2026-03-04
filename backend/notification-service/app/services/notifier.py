"""
WebSocket connection manager with per-student targeting.

Each student can have multiple active connections (e.g. multiple tabs).
Messages are routed to the specific student's connections rather than
broadcast to everyone.
"""
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# student_id → list of WebSocket connections
_connections: Dict[str, List[WebSocket]] = defaultdict(list)
_total_messages_sent: int = 0
_failed_deliveries: int = 0


def get_active_connection_count() -> int:
    return sum(len(ws_list) for ws_list in _connections.values())


def get_total_messages_sent() -> int:
    return _total_messages_sent


def get_failed_deliveries() -> int:
    return _failed_deliveries


def get_unique_students() -> int:
    return len(_connections)


async def connect(websocket: WebSocket, student_id: str) -> None:
    """Accept and register a WebSocket connection under a student ID."""
    await websocket.accept()
    _connections[student_id].append(websocket)
    logger.info(
        "WebSocket connected: student_id=%s  active=%d",
        student_id, get_active_connection_count(),
    )


def disconnect(websocket: WebSocket, student_id: str) -> None:
    """Remove a WebSocket connection from the active pool."""
    ws_list = _connections.get(student_id, [])
    if websocket in ws_list:
        ws_list.remove(websocket)
    if not ws_list and student_id in _connections:
        del _connections[student_id]
    logger.info(
        "WebSocket disconnected: student_id=%s  active=%d",
        student_id, get_active_connection_count(),
    )


async def send_to_student(student_id: str, message: str) -> int:
    """
    Send a message to all connections belonging to a specific student.

    Returns the number of successful deliveries.
    """
    global _total_messages_sent, _failed_deliveries
    ws_list = _connections.get(student_id, [])
    if not ws_list:
        logger.debug("No active connections for student_id=%s", student_id)
        return 0

    delivered = 0
    dead: List[WebSocket] = []
    for ws in list(ws_list):
        try:
            await ws.send_text(message)
            _total_messages_sent += 1
            delivered += 1
        except Exception as exc:
            logger.warning("Failed to send to student %s: %s", student_id, exc)
            _failed_deliveries += 1
            dead.append(ws)

    for ws in dead:
        disconnect(ws, student_id)
    return delivered


async def broadcast(message: str) -> int:
    """Broadcast a message to ALL active WebSocket clients (admin use)."""
    global _total_messages_sent, _failed_deliveries
    delivered = 0
    dead: List[tuple] = []
    for student_id, ws_list in list(_connections.items()):
        for ws in list(ws_list):
            try:
                await ws.send_text(message)
                _total_messages_sent += 1
                delivered += 1
            except Exception as exc:
                logger.warning("Broadcast failed for student %s: %s", student_id, exc)
                _failed_deliveries += 1
                dead.append((ws, student_id))

    for ws, sid in dead:
        disconnect(ws, sid)
    return delivered
