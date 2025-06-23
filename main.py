import json
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from utils.whisper_utils import transcribe_file
import tempfile

app = FastAPI()

# Allow CORS (required for frontend on different origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory connected users (username → WebSocket)
connected_users: Dict[str, WebSocket] = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connected_users[username] = websocket
    print(f"[CONNECTED] {username}")

    # Notify others about new connection
    for user, ws in connected_users.items():
        if user != username:
            try:
                await ws.send_json({"type": "user_connected", "username": username})
            except:
                pass  # Avoid breaking others

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[MESSAGE] From {username}: {data}")
            message = json.loads(data)

            # Route message to intended recipient
            to_user = message.get("to")
            if to_user in connected_users:
                await connected_users[to_user].send_text(data)
            else:
                print(f"[WARN] {to_user} is not connected")

    except WebSocketDisconnect:
        print(f"[DISCONNECTED] {username}")
    finally:
        connected_users.pop(username, None)

        # Notify others about disconnection
        for user, ws in connected_users.items():
            try:
                await ws.send_json({"type": "user_disconnected", "username": username})
            except:
                pass


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        segments, _ = transcribe_file(tmp.name)
        text = " ".join([s.text.strip() for s in segments])
        print(f"[TRANSCRIBED] {text}")
        return {"text": text}
