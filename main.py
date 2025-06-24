from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import tempfile, os, subprocess
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

# 📌 Track users and their transcript history
connected_users: Dict[str, WebSocket] = {}
user_transcripts: Dict[str, str] = {}

# 🔤 Transcription with Whisper
def transcribe_with_openai(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text

# 🖼️ Image generation with DALL·E 3
def generate_image_from_prompt(prompt: str) -> str:
    response = client.images.generate(
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
                # Step 1: Save audio blob as .webm
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_webm:
                    tmp_webm.write(message["bytes"])
                    webm_path = tmp_webm.name

                # Step 2: Convert .webm to .mp3 using ffmpeg
                mp3_path = webm_path.replace(".webm", ".mp3")
                try:
                    subprocess.run([
                        "ffmpeg", "-y", "-i", webm_path,
                        "-ar", "16000", "-ac", "1", mp3_path
                    ], check=True)

                    # Step 3: Transcribe audio
                    partial_transcript = transcribe_with_openai(mp3_path)

                    if not partial_transcript.strip():
                        continue

                    # Step 4: Store full transcript
                    full_text = user_transcripts.get(username, "")
                    if partial_transcript not in full_text:
                        full_text += " " + partial_transcript
                        user_transcripts[username] = full_text.strip()

                        # Step 5: Generate image from updated transcript
                        try:
                            image_url = generate_image_from_prompt(full_text.strip())
                            print(f"🖼️ Image created for: {full_text.strip()}")

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

                finally:
                    os.remove(webm_path)
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected")
        connected_users.pop(username, None)
        user_transcripts.pop(username, None)