import logging

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.config import JWT_SECRET, JWT_ALGORITHM
from app.services.notifier import connect, disconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def _validate_ws_token(token: str | None) -> str | None:
    """Decode a JWT and return the student_id, or None on failure."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("student_id")
    except jwt.PyJWTError as exc:
        logger.warning("WS token validation failed: %s", exc)
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """
    Real-time notification endpoint for connected students.

    Connect with: ``ws://host/ws?token=<jwt>``
    """
    student_id = _validate_ws_token(token)
    if student_id is None:
        await websocket.close(code=1008, reason="Invalid or missing token")
        return

    await connect(websocket, student_id)
    try:
        while True:
            # Keep the connection alive — client may send pings/pongs
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect(websocket, student_id)
    except Exception:
        disconnect(websocket, student_id)
