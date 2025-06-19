from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import tempfile
import os
import wave
import uvicorn
from faster_whisper import WhisperModel

app = FastAPI()

# CORS for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your specific frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections: Dict[str, WebSocket] = {}
model = WhisperModel("base.en", compute_type="int8")

@app.websocket("/ws/{username}")
async def signaling(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            for name, conn in active_connections.items():
                if conn != websocket:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        del active_connections[username]

@app.websocket("/transcribe")
async def transcribe(websocket: WebSocket):
    await websocket.accept()
    print("🎤 Transcription started")

    buffer = b""
    try:
        while True:
            chunk = await websocket.receive_bytes()
            buffer += chunk

            if len(buffer) > 16000 * 2 * 3:  # ~3s of audio
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    wav_path = f.name
                    with wave.open(f, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(buffer)

                segments, _ = model.transcribe(wav_path)
                for segment in segments:
                    text = segment.text.strip()
                    if text:
                        await websocket.send_text(text)

                os.remove(wav_path)
                buffer = b""

    except WebSocketDisconnect:
        print("🛑 Transcription ended")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
