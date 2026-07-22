import subprocess
from pathlib import Path
from typing import List, Tuple

from app.config import KEYFRAMES_DIR, AUDIO_DIR, KEYFRAME_INTERVAL_SECONDS, KEYFRAME_MAX_WIDTH


def extract_keyframes(clip_id: int, video_path: str) -> List[Tuple[str, float]]:
    """Extract keyframes at regular intervals. Returns list of (frame_path, timestamp_seconds)."""
    out_dir = KEYFRAMES_DIR / str(clip_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"fps=1/{KEYFRAME_INTERVAL_SECONDS},scale={KEYFRAME_MAX_WIDTH}:-2",
            "-q:v", "3",
            str(out_dir / "frame_%05d.jpg"),
        ],
        capture_output=True, timeout=300,
    )

    frames = sorted(out_dir.glob("frame_*.jpg"))
    result = []
    for i, frame in enumerate(frames):
        timestamp = i * KEYFRAME_INTERVAL_SECONDS
        result.append((str(frame), float(timestamp)))
    return result


def extract_audio(clip_id: int, video_path: str) -> str:
    """Extract audio as 16kHz mono WAV. Returns audio file path."""
    audio_path = AUDIO_DIR / f"{clip_id}.wav"
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(audio_path),
        ],
        capture_output=True, timeout=300,
    )
    return str(audio_path)
