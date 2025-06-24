from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from utils.whisper_utils import transcribe_file
from utils.image_utils import generate_image_from_prompt
import tempfile, ffmpeg, os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_users: Dict[str, WebSocket] = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connected_users[username] = websocket
    print(f"✅ {username} connected")

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                audio_data = message["bytes"]

                # 1️⃣ Save chunk to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name

                # 2️⃣ Convert to WAV (16000Hz, mono)
                wav_path = tmp_path.replace(".webm", ".wav")
                ffmpeg.input(tmp_path).output(
                    wav_path,
                    format='wav',
                    ac=1,
                    ar='16000'
                ).run(overwrite_output=True, quiet=True)

                # 3️⃣ Transcribe
                transcription = transcribe_file(wav_path)
                print(f"📝 {username}: {transcription}")

                # 4️⃣ Generate image
                image_url = generate_image_from_prompt(transcription)
                print(f"🖼️ Image: {image_url}")

                # 5️⃣ Respond to client
                await websocket.send_json({
                    "from": username,
                    "transcription": transcription,
                    "image_url": image_url
                })

                # 🔚 Cleanup
                os.remove(tmp_path)
                os.remove(wav_path)

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected")
        connected_users.pop(username, None)
