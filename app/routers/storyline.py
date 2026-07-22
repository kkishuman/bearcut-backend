from __future__ import annotations

import json
import threading
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Project, Clip, ClipAnalysis, Storyline, EditPlan
from app.schemas import StorylineOut, EditPlanOut, SegmentPatch
from app.services.storyline_service import generate_storyline

router = APIRouter(prefix="/api/v1", tags=["storyline"])


@router.post("/projects/{project_id}/storyline")
def create_storyline(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    analyzed = (
        db.query(func.count(ClipAnalysis.id))
        .join(Clip, Clip.id == ClipAnalysis.clip_id)
        .filter(Clip.project_id == project_id, ClipAnalysis.status == "complete")
        .scalar()
    )
    if not analyzed:
        raise HTTPException(400, "No analyzed clips available")

    max_version = (
        db.query(func.max(Storyline.version))
        .filter(Storyline.project_id == project_id)
        .scalar()
    ) or 0

    storyline = Storyline(project_id=project_id, version=max_version + 1, status="generating")
    db.add(storyline)
    db.commit()
    db.refresh(storyline)

    thread = threading.Thread(
        target=generate_storyline,
        args=(project_id, SessionLocal, storyline.id),
        daemon=True,
    )
    thread.start()

    return {"storyline_id": storyline.id, "status": "generating"}


@router.get("/storylines/{storyline_id}", response_model=StorylineOut)
def get_storyline(storyline_id: int, db: Session = Depends(get_db)):
    storyline = db.get(Storyline, storyline_id)
    if not storyline:
        raise HTTPException(404, "Storyline not found")
    return storyline


@router.get("/projects/{project_id}/storylines", response_model=List[StorylineOut])
def list_storylines(project_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Storyline)
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.version.desc())
        .all()
    )


@router.get("/storylines/{storyline_id}/edit-plan", response_model=List[EditPlanOut])
def get_edit_plan(storyline_id: int, db: Session = Depends(get_db)):
    return (
        db.query(EditPlan)
        .filter(EditPlan.storyline_id == storyline_id)
        .order_by(EditPlan.segment_id, EditPlan.order_in_segment)
        .all()
    )


@router.patch("/storylines/{storyline_id}/segments/{segment_id}")
def patch_segment(storyline_id: int, segment_id: str, body: SegmentPatch, db: Session = Depends(get_db)):
    storyline = db.get(Storyline, storyline_id)
    if not storyline:
        raise HTTPException(404, "Storyline not found")

    segments = json.loads(storyline.segments) if storyline.segments else []
    found = False
    for seg in segments:
        if seg["segment_id"] == segment_id:
            if body.status is not None:
                seg["status"] = body.status
            if body.order is not None:
                seg["order"] = body.order
            found = True
            break

    if not found:
        raise HTTPException(404, "Segment not found")

    segments.sort(key=lambda s: s["order"])
    storyline.segments = json.dumps(segments)
    db.commit()
    return {"ok": True}


@router.post("/storylines/{storyline_id}/regenerate")
def regenerate_storyline(storyline_id: int, db: Session = Depends(get_db)):
    old = db.get(Storyline, storyline_id)
    if not old:
        raise HTTPException(404, "Storyline not found")

    previous_segments = json.loads(old.segments) if old.segments else []

    previous_summaries = [
        s for (s,) in db.query(Storyline.narrative_summary)
        .filter(
            Storyline.project_id == old.project_id,
            Storyline.status == "complete",
            Storyline.narrative_summary.isnot(None),
        )
        .order_by(Storyline.version)
        .all()
        if s
    ]

    max_version = (
        db.query(func.max(Storyline.version))
        .filter(Storyline.project_id == old.project_id)
        .scalar()
    ) or 0

    new_storyline = Storyline(
        project_id=old.project_id,
        version=max_version + 1,
        status="generating",
    )
    db.add(new_storyline)
    db.commit()
    db.refresh(new_storyline)

    thread = threading.Thread(
        target=generate_storyline,
        args=(old.project_id, SessionLocal, new_storyline.id, previous_segments, previous_summaries),
        daemon=True,
    )
    thread.start()

    return {"storyline_id": new_storyline.id, "status": "generating"}
