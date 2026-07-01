"""Derived state cache — ``.resume-state.json``.

In v2 this file is a *derived cache*, not the source of truth.
It is rebuilt from the KB by ``tools.state_builder`` whenever needed.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from .base import ExperienceLevel, SchemaBase


class StateCounts(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    projects: int = 0
    skills: int = 0
    jds: int = 0
    resumes: int = 0
    verified_projects: int = 0
    outcomes_events: int = 0


class StateTimestamps(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    last_intake_at: Optional[datetime] = None
    last_match_at: Optional[datetime] = None
    last_build_at: Optional[datetime] = None
    last_interview_at: Optional[datetime] = None
    last_verify_at: Optional[datetime] = None
    last_track_at: Optional[datetime] = None


class ResumeState(SchemaBase):
    """Root schema for ``.resume-state.json`` (persisted as JSON for legacy readability)."""

    schema_type: Literal["state"] = "state"

    skill_version: str = "2.0.0-dev"
    target_role: Optional[str] = None
    target_industry: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    active_jd_id: Optional[str] = None
    pending_learning: List[str] = Field(default_factory=list)
    counts: StateCounts = Field(default_factory=StateCounts)
    timestamps: StateTimestamps = Field(default_factory=StateTimestamps)
    initialized_at: Optional[datetime] = None
    rebuilt_at: Optional[datetime] = None
