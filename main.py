from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uvicorn

app = FastAPI()

# Allow frontend from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active connections
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    print(f"🔌 {username} connected.")
    active_connections[username] = websocket

    try:
        while True:
            data = await websocket.receive_text()

            # Forward the message to other connected users
            for target_name, target_ws in active_connections.items():
                if target_ws != websocket:
                    await target_ws.send_text(data)

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected.")
        if username in active_connections:
            del active_connections[username]

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
