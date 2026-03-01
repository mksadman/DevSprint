from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.notifier import connect, disconnect, send_personal_message

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time notification endpoint for connected clients."""
    await connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await send_personal_message(websocket, f"echo: {data}")
    except WebSocketDisconnect:
        disconnect(websocket)
