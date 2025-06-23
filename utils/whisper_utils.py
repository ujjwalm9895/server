from faster_whisper import WhisperModel

# Load once at startup
model = WhisperModel("base.en", compute_type="int8")  # Change to "tiny.en" if needed

def transcribe_file(path: str):
    segments, info = model.transcribe(path)
    return list(segments), info