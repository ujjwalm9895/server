from faster_whisper import WhisperModel

# Load once when the server starts
model = WhisperModel("base", compute_type="int8")  # Use "base" or "tiny" for small servers

def transcribe_file(path: str):
    segments, info = model.transcribe(path)
    return list(segments), info
