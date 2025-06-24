from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from utils.image_utils import generate_image_from_prompt
import tempfile, os
from typing import Dict
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_users: Dict[str, WebSocket] = {}

def transcribe_with_openai(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript["text"]

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

                # Save audio chunk temporarily (webm works directly with OpenAI!)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name

                # Transcribe with OpenAI
                try:
                    transcription = transcribe_with_openai(tmp_path)
                    print(f"📝 {username}: {transcription}")
                except Exception as e:
                    print("❌ Transcription error:", str(e))
                    await websocket.send_json({
                        "error": "Transcription failed."
                    })
                    os.remove(tmp_path)
                    return

                # Generate image
                try:
                    image_url = generate_image_from_prompt(transcription)
                    print(f"🖼️ Image: {image_url}")
                except Exception as e:
                    print("❌ Image generation error:", str(e))
                    await websocket.send_json({
                        "error": "Image generation failed."
                    })
                    os.remove(tmp_path)
                    return

                # Respond to frontend
                await websocket.send_json({
                    "from": username,
                    "transcription": transcription,
                    "image_url": image_url
                })

                os.remove(tmp_path)

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected")
        connected_users.pop(username, None)
