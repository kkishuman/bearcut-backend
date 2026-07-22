from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Integer, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow, onupdate=utcnow)

    clips: Mapped[List[Clip]] = relationship(back_populates="project", cascade="all, delete-orphan")
    preferences: Mapped[Optional[Preferences]] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
    storylines: Mapped[List[Storyline]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    upload_order: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="clips")
    analysis: Mapped[Optional[ClipAnalysis]] = relationship(back_populates="clip", cascade="all, delete-orphan", uselist=False)


class ClipAnalysis(Base):
    __tablename__ = "clip_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(ForeignKey("clips.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    transcript: Mapped[Optional[str]] = mapped_column(Text)
    keyframe_descriptions: Mapped[Optional[str]] = mapped_column(Text)
    scene_summary: Mapped[Optional[str]] = mapped_column(Text)
    detected_moments: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[str]] = mapped_column(Text)
    completed_at: Mapped[Optional[str]] = mapped_column(Text)

    clip: Mapped[Clip] = relationship(back_populates="analysis")


class Preferences(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    pacing: Mapped[str] = mapped_column(Text, default="medium")
    tone: Mapped[str] = mapped_column(Text, default="casual")
    target_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    vlog_type: Mapped[str] = mapped_column(Text, default="other")
    target_platform: Mapped[str] = mapped_column(Text, default="none")
    must_include: Mapped[Optional[str]] = mapped_column(Text)
    must_exclude: Mapped[Optional[str]] = mapped_column(Text)
    additional_notes: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow, onupdate=utcnow)

    project: Mapped[Project] = relationship(back_populates="preferences")


class Storyline(Base):
    __tablename__ = "storylines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(Text, default="generating")
    narrative_summary: Mapped[Optional[str]] = mapped_column(Text)
    segments: Mapped[Optional[str]] = mapped_column(Text)
    director_statement: Mapped[Optional[str]] = mapped_column(Text)
    reshoot_list: Mapped[Optional[str]] = mapped_column(Text)
    publishing_suggestions: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="storylines")
    edit_plans: Mapped[List[EditPlan]] = relationship(back_populates="storyline", cascade="all, delete-orphan")


class EditPlan(Base):
    __tablename__ = "edit_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storyline_id: Mapped[int] = mapped_column(ForeignKey("storylines.id", ondelete="CASCADE"))
    segment_id: Mapped[str] = mapped_column(Text, nullable=False)
    clip_id: Mapped[int] = mapped_column(ForeignKey("clips.id"))
    in_timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    out_timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    order_in_segment: Mapped[Optional[int]] = mapped_column(Integer)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    transition_note: Mapped[Optional[str]] = mapped_column(Text)
    clip_summary: Mapped[Optional[str]] = mapped_column(Text)
    purpose: Mapped[Optional[str]] = mapped_column(Text)

    storyline: Mapped[Storyline] = relationship(back_populates="edit_plans")
