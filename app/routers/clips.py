from __future__ import annotations

import shutil
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import VIDEOS_DIR
from app.database import get_db
from app.models import Project, Clip, ClipAnalysis
from app.schemas import ClipOut, AnalysisStatusOut
from app.services.clip_service import probe_video
from app.services.thumbnail_service import get_or_create_thumbnail

router = APIRouter(prefix="/api/v1", tags=["clips"])


@router.post("/projects/{project_id}/clips", response_model=List[ClipOut], status_code=201)
async def upload_clips(
    project_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    existing_count = db.query(Clip).filter(Clip.project_id == project_id).count()
    project_dir = VIDEOS_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, upload in enumerate(files):
        clip = Clip(
            project_id=project_id,
            filename=upload.filename or f"clip_{existing_count + i + 1}",
            file_path="",
            upload_order=existing_count + i + 1,
        )
        db.add(clip)
        db.flush()

        ext = (upload.filename or "").rsplit(".", 1)[-1] if upload.filename and "." in upload.filename else "mp4"
        dest = project_dir / f"{clip.id}.{ext}"
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        clip.file_path = str(dest)
        duration, resolution, file_size = probe_video(str(dest))
        clip.duration_seconds = duration
        clip.resolution = resolution
        clip.file_size_bytes = file_size

        db.flush()
        results.append(clip)

    db.commit()

    return [
        ClipOut(
            id=c.id,
            project_id=c.project_id,
            filename=c.filename,
            duration_seconds=c.duration_seconds,
            resolution=c.resolution,
            file_size_bytes=c.file_size_bytes,
            upload_order=c.upload_order,
            created_at=c.created_at,
            analysis_status=None,
        )
        for c in results
    ]


@router.get("/projects/{project_id}/clips", response_model=List[ClipOut])
def list_clips(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    clips = (
        db.query(Clip, ClipAnalysis.status)
        .outerjoin(ClipAnalysis, ClipAnalysis.clip_id == Clip.id)
        .filter(Clip.project_id == project_id)
        .order_by(Clip.upload_order)
        .all()
    )

    return [
        ClipOut(
            id=c.id,
            project_id=c.project_id,
            filename=c.filename,
            duration_seconds=c.duration_seconds,
            resolution=c.resolution,
            file_size_bytes=c.file_size_bytes,
            upload_order=c.upload_order,
            created_at=c.created_at,
            analysis_status=status,
        )
        for c, status in clips
    ]


@router.get("/clips/{clip_id}/thumbnail")
def get_clip_thumbnail(clip_id: int, t: float = 0.0, db: Session = Depends(get_db)):
    clip = db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(404, "Clip not found")
    path = get_or_create_thumbnail(clip_id, clip.file_path, max(0.0, t))
    if not path:
        raise HTTPException(500, "Failed to generate thumbnail")
    return FileResponse(str(path), media_type="image/jpeg")


@router.delete("/clips/{clip_id}", status_code=204)
def delete_clip(clip_id: int, db: Session = Depends(get_db)):
    clip = db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(404, "Clip not found")
    from pathlib import Path
    path = Path(clip.file_path)
    if path.exists():
        path.unlink()
    db.delete(clip)
    db.commit()
