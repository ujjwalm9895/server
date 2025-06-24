from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import tempfile, os
from typing import Dict
from dotenv import load_dotenv
import openai

# Load OpenAI key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Allow frontend access (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, limit this to your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track users and their transcript history
connected_users: Dict[str, WebSocket] = {}
user_transcripts: Dict[str, str] = {}

# 🔤 Transcribe audio using Whisper (OpenAI)
def transcribe_with_openai(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript["text"]

# 🖼️ Generate image using DALL·E 3
def generate_image_from_prompt(prompt: str) -> str:
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    return response.data[0].url

# 🔌 WebSocket endpoint
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connected_users[username] = websocket
    user_transcripts[username] = ""
    print(f"✅ {username} connected")

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                # 🎙️ Save received audio chunk
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                    tmp.write(message["bytes"])
                    tmp_path = tmp.name

                try:
                    # 🔤 Transcribe audio
                    partial_transcript = transcribe_with_openai(tmp_path)
                    os.remove(tmp_path)

                    if not partial_transcript.strip():
                        continue

                    full_text = user_transcripts.get(username, "")
                    if partial_transcript not in full_text:
                        full_text += " " + partial_transcript
                        user_transcripts[username] = full_text.strip()

                        # 🖼️ Generate image
                        try:
                            image_url = generate_image_from_prompt(full_text.strip())
                            print(f"🖼️ Image created for: {full_text.strip()}")

                            # 📤 Send image + transcript
                            await websocket.send_json({
                                "from": username,
                                "transcription": full_text.strip(),
                                "image_url": image_url
                            })
                        except Exception as e:
                            print("❌ Image error:", e)
                            await websocket.send_json({"error": "Image generation failed"})
                except Exception as e:
                    print("❌ Transcription error:", e)
                    await websocket.send_json({"error": "Transcription failed"})

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected")
        connected_users.pop(username, None)
        user_transcripts.pop(username, None)
