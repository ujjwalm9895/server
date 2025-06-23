from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from utils.whisper_utils import transcribe_file
import tempfile, ffmpeg, os
from typing import Dict

app = FastAPI()

# CORS: allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected users for WebSocket
connected_users: Dict[str, WebSocket] = {}

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

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_in:
            contents = await file.read()
            print("📥 Received audio size:", len(contents))
            tmp_in.write(contents)
            tmp_in.flush()
            input_path = tmp_in.name
            output_path = input_path.replace(".webm", ".wav")

        # Convert .webm → .wav using ffmpeg
        ffmpeg.input(input_path).output(output_path, ar=16000, ac=1).run(overwrite_output=True)

        # Transcribe with Whisper
        segments, _ = transcribe_file(output_path)
        text = " ".join([s.text.strip() for s in segments])

        # Clean up temp files
        os.remove(input_path)
        os.remove(output_path)

        print(f"[TRANSCRIBED] {text}")
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}
