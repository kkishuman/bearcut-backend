from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Preferences
from app.schemas import PreferencesUpdate, PreferencesOut

router = APIRouter(prefix="/api/v1", tags=["preferences"])


@router.get("/projects/{project_id}/preferences", response_model=PreferencesOut)
def get_preferences(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    prefs = db.query(Preferences).filter(Preferences.project_id == project_id).first()
    if not prefs:
        prefs = Preferences(project_id=project_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return prefs


@router.put("/projects/{project_id}/preferences", response_model=PreferencesOut)
def update_preferences(project_id: int, body: PreferencesUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    prefs = db.query(Preferences).filter(Preferences.project_id == project_id).first()
    if not prefs:
        prefs = Preferences(project_id=project_id)
        db.add(prefs)

    if body.pacing is not None:
        prefs.pacing = body.pacing
    if body.tone is not None:
        prefs.tone = body.tone
    if body.target_duration_seconds is not None:
        prefs.target_duration_seconds = body.target_duration_seconds
    if body.vlog_type is not None:
        prefs.vlog_type = body.vlog_type
    if body.target_platform is not None:
        prefs.target_platform = body.target_platform
    if body.must_include is not None:
        prefs.must_include = json.dumps(body.must_include)
    if body.must_exclude is not None:
        prefs.must_exclude = json.dumps(body.must_exclude)
    if body.additional_notes is not None:
        prefs.additional_notes = body.additional_notes

    db.commit()
    db.refresh(prefs)
    return prefs
