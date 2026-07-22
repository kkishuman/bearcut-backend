from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / "backend" / ".env", override=True)
load_dotenv(BASE_DIR / ".env", override=True)
STORAGE_DIR = BASE_DIR / "storage"
VIDEOS_DIR = STORAGE_DIR / "videos"
KEYFRAMES_DIR = STORAGE_DIR / "keyframes"
AUDIO_DIR = STORAGE_DIR / "audio"
THUMBS_DIR = STORAGE_DIR / "thumbs"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'bearcut.db'}"

CLAUDE_MODEL = "claude-sonnet-4-20250514"
WHISPER_MODEL = "base"
KEYFRAME_INTERVAL_SECONDS = 3
KEYFRAME_MAX_WIDTH = 1280
VISION_BATCH_SIZE = 8
