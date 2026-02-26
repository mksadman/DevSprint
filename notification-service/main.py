from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Notification Service", version="1.0.0")


@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    return {"status": "ok", "service": "notification-service"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Placeholder WebSocket endpoint for real-time notifications."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        pass
