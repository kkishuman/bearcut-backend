from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Clip, ClipAnalysis
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut, ProjectDetail

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _project_query(db: Session):
    return (
        db.query(
            Project,
            func.count(Clip.id).label("clip_count"),
            func.sum(
                case((ClipAnalysis.status == "complete", 1), else_=0)
            ).label("analysis_complete_count"),
        )
        .outerjoin(Clip, Clip.project_id == Project.id)
        .outerjoin(ClipAnalysis, ClipAnalysis.clip_id == Clip.id)
        .group_by(Project.id)
    )


def _to_out(row) -> ProjectOut:
    project, clip_count, analysis_complete = row
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        clip_count=clip_count or 0,
        analysis_complete_count=analysis_complete or 0,
    )


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    rows = _project_query(db).order_by(Project.updated_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=body.name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    row = _project_query(db).filter(Project.id == project_id).first()
    if not row:
        raise HTTPException(404, "Project not found")
    return _to_out(row)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    db.commit()
    db.refresh(project)
    row = _project_query(db).filter(Project.id == project_id).first()
    return _to_out(row)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
