from faster_whisper import WhisperModel

model = WhisperModel("tiny.en", compute_type="int8")

def transcribe_file(path: str):
    segments, info = model.transcribe(path)
    return list(segments), info
