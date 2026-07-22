import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def probe_video(file_path: str) -> Tuple[Optional[float], Optional[str], Optional[int]]:
    """Extract duration, resolution, and file size using ffprobe."""
    path = Path(file_path)
    file_size = path.stat().st_size if path.exists() else None

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                file_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)

        duration = None
        if "format" in data and "duration" in data["format"]:
            duration = float(data["format"]["duration"])

        resolution = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                w = stream.get("width")
                h = stream.get("height")
                if w and h:
                    resolution = f"{w}x{h}"
                    break

        return duration, resolution, file_size
    except Exception:
        return None, None, file_size
