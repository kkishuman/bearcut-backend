import subprocess
from pathlib import Path
from typing import Optional

from app.config import THUMBS_DIR


def get_or_create_thumbnail(clip_id: int, video_path: str, timestamp: float) -> Optional[Path]:
    """Extract a precise frame at `timestamp` from the video. Caches output.
    Returns path to JPEG, or None on failure."""
    out_dir = THUMBS_DIR / str(clip_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Round to 0.1s for cache key
    rounded = round(timestamp, 1)
    out_path = out_dir / f"{rounded}.jpg"

    if out_path.exists():
        return out_path

    if not Path(video_path).exists():
        return None

    try:
        # -ss before -i is fast seek; accuracy good enough for thumbnails
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(rounded),
                "-i", video_path,
                "-frames:v", "1",
                "-vf", "scale=320:-2",
                "-q:v", "3",
                str(out_path),
            ],
            capture_output=True, timeout=30,
        )
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path
    except Exception:
        pass
    return None
