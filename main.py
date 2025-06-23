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
connected_users = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connected_users[username] = websocket
    await broadcast({"type": "user_connected", "username": username}, exclude=username)

    try:
        while True:
            data = await websocket.receive_text()
            for_send = data
            for key, ws in connected_users.items():
                if key != username:
                    await ws.send_text(for_send)
    except WebSocketDisconnect:
        del connected_users[username]
        await broadcast({"type": "user_disconnected", "username": username}, exclude=username)


async def broadcast(message: dict, exclude: str = None):
    for user, ws in connected_users.items():
        if user != exclude:
            await ws.send_json(message)


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        segments, _ = transcribe_file(tmp.name)
        text = " ".join([s.text.strip() for s in segments])
        print(f"[TRANSCRIBED] {text}")
        return {"text": text}
