from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Clip, ClipAnalysis
from app.schemas import AnalysisStatusOut, ClipAnalysisOut
from app.services.task_manager import enqueue_clip_analyses

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/projects/{project_id}/analyze")
def trigger_analysis(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    clips = db.query(Clip).filter(Clip.project_id == project_id).all()
    if not clips:
        raise HTTPException(400, "No clips to analyze")

    clip_ids_to_analyze = []
    for clip in clips:
        analysis = db.query(ClipAnalysis).filter(ClipAnalysis.clip_id == clip.id).first()
        if not analysis:
            analysis = ClipAnalysis(clip_id=clip.id, status="pending")
            db.add(analysis)
            clip_ids_to_analyze.append(clip.id)
        elif analysis.status in ("failed",):
            analysis.status = "pending"
            analysis.error_message = None
            clip_ids_to_analyze.append(clip.id)

    db.commit()

    if clip_ids_to_analyze:
        enqueue_clip_analyses(clip_ids_to_analyze)

    return {"clips_queued": len(clip_ids_to_analyze)}


@router.get("/projects/{project_id}/analysis-status", response_model=List[AnalysisStatusOut])
def analysis_status(project_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Clip.id, Clip.filename, ClipAnalysis.status)
        .outerjoin(ClipAnalysis, ClipAnalysis.clip_id == Clip.id)
        .filter(Clip.project_id == project_id)
        .order_by(Clip.upload_order)
        .all()
    )
    return [
        AnalysisStatusOut(clip_id=clip_id, filename=filename, status=status)
        for clip_id, filename, status in rows
    ]


@router.get("/clips/{clip_id}/analysis", response_model=ClipAnalysisOut)
def get_clip_analysis(clip_id: int, db: Session = Depends(get_db)):
    analysis = db.query(ClipAnalysis).filter(ClipAnalysis.clip_id == clip_id).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    return analysis
