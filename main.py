from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import tempfile, os
from typing import Dict
from dotenv import load_dotenv
import openai

# Load .env file and OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connections and transcript history
connected_users: Dict[str, WebSocket] = {}
user_transcripts: Dict[str, str] = {}

# 🔤 Whisper transcription using OpenAI
def transcribe_with_openai(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript["text"]

# 🎨 Image generation using OpenAI DALL·E 3
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
                # 🎙️ Save audio to a temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                    tmp.write(message["bytes"])
                    tmp_path = tmp.name

                try:
                    # 🔤 Transcribe new audio chunk
                    partial_transcript = transcribe_with_openai(tmp_path)
                    os.remove(tmp_path)

                    if not partial_transcript.strip():
                        continue

                    print(f"🗣️ {username} spoke: {partial_transcript}")
                    full_text = user_transcripts.get(username, "")

                    # 👀 Only update if new words
                    if partial_transcript not in full_text:
                        full_text += " " + partial_transcript
                        user_transcripts[username] = full_text.strip()

                        # 🖼️ Generate image from updated transcript
                        try:
                            image_url = generate_image_from_prompt(full_text.strip())
                            print(f"🖼️ DALL·E image generated: {image_url}")

                            # 📤 Send data back to client
                            await websocket.send_json({
                                "from": username,
                                "transcription": full_text.strip(),
                                "image_url": image_url
                            })
                        except Exception as e:
                            print("❌ DALL·E error:", e)
                            await websocket.send_json({"error": "Image generation failed"})
                except Exception as e:
                    print("❌ Whisper error:", e)
                    await websocket.send_json({"error": "Transcription failed"})

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected")
        connected_users.pop(username, None)
        user_transcripts.pop(username, None)
