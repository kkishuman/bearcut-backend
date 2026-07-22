import threading
from typing import List

from app.database import SessionLocal
from app.services.analysis_service import run_clip_analysis

_lock = threading.Lock()
_running = False


def enqueue_clip_analyses(clip_ids: List[int]):
    """Process clips sequentially in a background thread."""
    global _running
    with _lock:
        if _running:
            return
        _running = True

    def worker():
        global _running
        try:
            for clip_id in clip_ids:
                run_clip_analysis(clip_id, SessionLocal)
        finally:
            with _lock:
                _running = False

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
