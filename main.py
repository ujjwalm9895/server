from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from utils.whisper_utils import transcribe_audio
from utils.dalle_utils import generate_image
from utils.memory_utils import save_transcript, get_followups

import json
import io

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/{username}")
async def signaling(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            for user, conn in active_connections.items():
                if user != username:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        active_connections.pop(username, None)

@app.websocket("/ws-ai")
async def ai_socket(websocket: WebSocket):
    await websocket.accept()
    buffer = io.BytesIO()
    full_transcript = []

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            buffer.write(audio_chunk)

            if buffer.tell() > 16000 * 10:  # ~10 sec
                buffer.seek(0)
                audio_bytes = buffer.read()
                buffer = io.BytesIO()

                text = transcribe_audio(audio_bytes)
                full_transcript.append(text)

                image_url = generate_image(text)

                await websocket.send_json({"image_url": image_url})
    except WebSocketDisconnect:
        save_transcript("temp_user", full_transcript)

@app.get("/followup/{username}")
async def followup(username: str):
    ideas = get_followups(username)
    return {"suggestion": ideas}
