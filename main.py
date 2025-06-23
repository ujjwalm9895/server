from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

app = FastAPI()

# Allow requests from any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections with usernames as keys
active_connections: Dict[str, WebSocket] = {}

# WebSocket route for signaling
@app.websocket("/ws/{username}")
async def signaling(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    print(f"✅ {username} connected. Active users: {list(active_connections.keys())}")

    try:
        while True:
            data = await websocket.receive_text()
            # Optionally parse the JSON to check the type of signal
            for user, conn in active_connections.items():
                if user != username:
                    try:
                        await conn.send_text(data)
                    except Exception as e:
                        print(f"❌ Failed to send to {user}: {e}")
    except WebSocketDisconnect:
        # Remove user on disconnect
        print(f"❌ {username} disconnected.")
        active_connections.pop(username, None)

        # Notify other users that this user has disconnected
        disconnect_notice = {
            "type": "user_disconnected",
            "username": username
        }
        for user, conn in active_connections.items():
            try:
                await conn.send_text(json.dumps(disconnect_notice))
            except:
                continue
