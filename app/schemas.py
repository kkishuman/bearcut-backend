from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    clip_count: int = 0
    analysis_complete_count: int = 0

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectOut):
    pass


class ClipOut(BaseModel):
    id: int
    project_id: int
    filename: str
    duration_seconds: Optional[float]
    resolution: Optional[str]
    file_size_bytes: Optional[int]
    upload_order: Optional[int]
    created_at: str
    analysis_status: Optional[str] = None

    model_config = {"from_attributes": True}


class AnalysisStatusOut(BaseModel):
    clip_id: int
    filename: str
    status: Optional[str]


class ClipAnalysisOut(BaseModel):
    id: int
    clip_id: int
    status: str
    error_message: Optional[str]
    transcript: Optional[str]
    keyframe_descriptions: Optional[str]
    scene_summary: Optional[str]
    detected_moments: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

    model_config = {"from_attributes": True}


class PreferencesUpdate(BaseModel):
    pacing: Optional[str] = None
    tone: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    vlog_type: Optional[str] = None
    target_platform: Optional[str] = None
    must_include: Optional[List[str]] = None
    must_exclude: Optional[List[str]] = None
    additional_notes: Optional[str] = None


class PreferencesOut(BaseModel):
    id: int
    project_id: int
    pacing: str
    tone: str
    target_duration_seconds: Optional[int]
    vlog_type: str
    target_platform: str
    must_include: Optional[str]
    must_exclude: Optional[str]
    additional_notes: Optional[str]
    updated_at: str

    model_config = {"from_attributes": True}


class SegmentPatch(BaseModel):
    status: Optional[str] = None
    order: Optional[int] = None


class StorylineOut(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    narrative_summary: Optional[str]
    segments: Optional[str]
    director_statement: Optional[str] = None
    reshoot_list: Optional[str] = None
    publishing_suggestions: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class EditPlanOut(BaseModel):
    id: int
    storyline_id: int
    segment_id: str
    clip_id: int
    in_timestamp: float
    out_timestamp: float
    order_in_segment: Optional[int]
    reasoning: Optional[str]
    transition_note: Optional[str]
    clip_summary: Optional[str] = None
    purpose: Optional[str] = None

    model_config = {"from_attributes": True}
