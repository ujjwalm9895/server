from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uvicorn
import openai
import tempfile

# === Basic Setup ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = "sk-..."  # 🔑 Replace with your OpenAI key

# === VoIP Signaling ===
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    print(f"🔌 {username} connected.")
    active_connections[username] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            for target_name, target_ws in active_connections.items():
                if target_ws != websocket:
                    await target_ws.send_text(data)
    except WebSocketDisconnect:
        print(f"❌ {username} disconnected.")
        if username in active_connections:
            del active_connections[username]

# === AI Audio-to-Image WebSocket ===
@app.websocket("/ws-ai")
async def websocket_ai(websocket: WebSocket):
    await websocket.accept()
    print("🧠 AI WebSocket connected.")
    audio_data = b""

    try:
        while True:
            chunk = await websocket.receive_bytes()
            audio_data += chunk

            if len(audio_data) > 16000 * 5:  # ~5 seconds
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_audio:
                    tmp_audio.write(audio_data)
                    tmp_audio.flush()

                    with open(tmp_audio.name, "rb") as f:
                        transcript = openai.Audio.transcribe("whisper-1", f)

                prompt = f"Dreamlike AI-generated image of: {transcript['text']}"
                print(f"🎤 Prompt: {prompt}")

                image_response = openai.Image.create(
                    prompt=prompt,
                    n=1,
                    size="512x512"
                )

                image_url = image_response["data"][0]["url"]
                await websocket.send_json({"image_url": image_url})
                audio_data = b""

    except WebSocketDisconnect:
        print("❌ AI WebSocket disconnected.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
