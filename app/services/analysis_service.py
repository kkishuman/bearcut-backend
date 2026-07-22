import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Clip, ClipAnalysis
from app.services.ffmpeg_service import extract_keyframes, extract_audio
from app.services.whisper_service import transcribe
from app.services.vision_service import analyze_keyframes


def run_clip_analysis(clip_id: int, db_factory):
    """Run the full analysis pipeline for a single clip. Called in a background thread."""
    db: Session = db_factory()
    try:
        clip = db.get(Clip, clip_id)
        if not clip:
            return

        analysis = db.query(ClipAnalysis).filter(ClipAnalysis.clip_id == clip_id).first()
        if not analysis:
            analysis = ClipAnalysis(clip_id=clip_id, status="pending")
            db.add(analysis)
            db.commit()

        if analysis.status == "complete":
            return

        analysis.status = "extracting_frames"
        analysis.started_at = datetime.now(timezone.utc).isoformat()
        db.commit()

        frames = extract_keyframes(clip_id, clip.file_path)
        audio_path = extract_audio(clip_id, clip.file_path)

        analysis.status = "transcribing"
        db.commit()

        transcript = transcribe(audio_path)
        analysis.transcript = json.dumps(transcript)
        db.commit()

        analysis.status = "analyzing_visuals"
        db.commit()

        descriptions = analyze_keyframes(frames)
        analysis.keyframe_descriptions = json.dumps(descriptions)

        all_tags = set()
        for desc in descriptions:
            for tag in desc.get("tags", []):
                all_tags.add(tag)

        analysis.scene_summary = "; ".join(
            d.get("description", "")[:100] for d in descriptions[:5]
        )
        analysis.detected_moments = json.dumps([
            {"timestamp": d["timestamp"], "description": d["description"][:200]}
            for d in descriptions
            if any(kw in d.get("description", "").lower() for kw in ["reaction", "reveal", "surprise", "laugh", "emotion", "exciting"])
        ])

        analysis.status = "complete"
        analysis.completed_at = datetime.now(timezone.utc).isoformat()
        db.commit()

    except Exception as e:
        try:
            analysis = db.query(ClipAnalysis).filter(ClipAnalysis.clip_id == clip_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
