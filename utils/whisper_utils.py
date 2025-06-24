from faster_whisper import WhisperModel

model = WhisperModel("base.en", device="cpu")

def transcribe_file(file_path: str) -> str:
    segments, _ = model.transcribe(file_path)
    return " ".join([seg.text for seg in segments])
