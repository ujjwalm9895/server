from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import tempfile
from typing import Dict

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use your domain only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected users for WebSocket signaling
connected_users: Dict[str, WebSocket] = {}

# Load the Whisper model
model = WhisperModel("base.en", compute_type="int8")  # You can use "tiny", "base", "small" etc.

# WebSocket Signaling
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connected_users[username] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            for user, conn in connected_users.items():
                if user != username:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        print(f"{username} disconnected")
    finally:
        connected_users.pop(username, None)

# Transcription Endpoint
@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        segments, _ = model.transcribe(tmp.name)
        text = " ".join([s.text.strip() for s in segments])
        print(f"[TRANSCRIBED] {text}")
        return {"text": text}
