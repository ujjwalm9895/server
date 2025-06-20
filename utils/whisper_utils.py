from faster_whisper import WhisperModel

model = WhisperModel("base")

def transcribe_audio(audio_bytes: bytes) -> str:
    with open("temp.webm", "wb") as f:
        f.write(audio_bytes)
    segments, _ = model.transcribe("temp.webm")
    return " ".join([seg.text for seg in segments])
