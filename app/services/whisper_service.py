import json
from typing import List, Dict
from pathlib import Path

from app.config import WHISPER_MODEL


def transcribe(audio_path: str) -> List[Dict]:
    """Transcribe audio using OpenAI Whisper. Returns list of {start, end, text} segments."""
    if not Path(audio_path).exists():
        return []

    try:
        import whisper
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(audio_path, word_timestamps=True)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            })
        return segments
    except ImportError:
        return _transcribe_stub(audio_path)


def _transcribe_stub(audio_path: str) -> List[Dict]:
    """Fallback when whisper is not installed."""
    return [{"start": 0.0, "end": 1.0, "text": "[Whisper not installed — transcription unavailable]"}]
