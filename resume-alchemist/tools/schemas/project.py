"""Project schema — the core evidence unit.

Every claim in a resume must be backed by a project defined here.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import Field, model_validator

from .base import LocalizedString, ProficiencyLevel, SchemaBase


class VerificationMethod(str, Enum):
    """How the project data was obtained."""

    DIALOG = "dialog"           # STAR-guided conversation
    FILE_IMPORT = "file_import" # parsed from an existing resume
    CODE_TRACE = "code_trace"   # verified by scanning source code


class ProjectPeriod(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    start: str = Field(..., description="YYYY-MM.")
    end: Optional[str] = Field(default=None, description="YYYY-MM or None if ongoing.")


class ProjectLink(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: str = Field(..., description="E.g. code / doc / demo.")
    url: str
    private: bool = False


class ProjectMeta(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    name: LocalizedString
    period: ProjectPeriod
    role: str = Field(..., min_length=1)
    team_size: Optional[int] = Field(default=None, ge=1)
    company: Optional[str] = None
    links: List[ProjectLink] = Field(default_factory=list)


class STARStory(SchemaBase):
    """STAR narrative — all four fields are required by evidence_validator."""

    schema_version: Literal["2.0"] = "2.0"

    situation: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    result: str = Field(..., min_length=1)


class TechStack(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    primary: List[str] = Field(default_factory=list)
    secondary: List[str] = Field(default_factory=list)


class SkillUsage(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    name: str = Field(..., min_length=1)
    proficiency_demonstrated: ProficiencyLevel
    note: Optional[str] = None


class Achievement(SchemaBase):
    """A single measurable outcome. ``source`` MUST reference something concrete
    (metric dashboard, BI report, screenshot in ``evidence/``), never 'estimate'.
    """

    schema_version: Literal["2.0"] = "2.0"

    type: str = Field(
        ...,
        description="E.g. performance / business / cost / quality / team.",
    )
    metric: str = Field(..., min_length=1)
    before: Optional[str] = None
    after: Optional[str] = None
    delta: Optional[str] = Field(
        default=None,
        description="Human-readable delta, e.g. '-81%' or '+12pp'.",
    )
    source: str = Field(
        ...,
        min_length=1,
        description="Where the number came from — required for truth_first.",
    )

    @property
    def is_quantified(self) -> bool:
        """Heuristic: any of before/after/delta contains a digit."""
        for v in (self.before, self.after, self.delta):
            if v and any(ch.isdigit() for ch in v):
                return True
        return False


class InterviewPrep(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    biggest_challenge: Optional[str] = None
    solution_summary: Optional[str] = None
    lessons_learned: List[str] = Field(default_factory=list)
    if_redo: Optional[str] = None


class _Computed(SchemaBase):
    """Auto-derived fields. Overwritten on every validator run."""

    schema_version: Literal["2.0"] = "2.0"

    has_quantified_achievement: bool = False
    has_star_complete: bool = False
    evidence_files_count: int = 0


class Project(SchemaBase):
    """Root schema for ``profile/projects/<id>/data.yaml``."""

    schema_type: Literal["project"] = "project"

    id: str = Field(..., pattern=r"^proj-\d{3}-[\w\u4e00-\u9fff\-]+$")
    created_at: Optional[datetime] = None
    verified_by: VerificationMethod = VerificationMethod.DIALOG
    verification_score: Optional[int] = Field(default=None, ge=0, le=100)

    meta: ProjectMeta
    star: STARStory
    tech_stack: TechStack = Field(default_factory=TechStack)
    skills_used: List[SkillUsage] = Field(default_factory=list)
    achievements: List[Achievement] = Field(default_factory=list)
    interview_prep: InterviewPrep = Field(default_factory=InterviewPrep)

    computed: _Computed = Field(default_factory=_Computed, alias="_computed")

    @model_validator(mode="after")
    def _verification_score_only_for_code_trace(self) -> "Project":
        if (
            self.verified_by != VerificationMethod.CODE_TRACE
            and self.verification_score is not None
        ):
            raise ValueError(
                "verification_score is only allowed when verified_by == 'code_trace'"
            )
        return self

    def recompute(self) -> "Project":
        """Refresh ``_computed`` fields. Call after any mutation."""
        self.computed.has_quantified_achievement = any(
            a.is_quantified for a in self.achievements
        )
        # STAR completeness is guaranteed at type level (all fields required non-empty).
        self.computed.has_star_complete = bool(
            self.star.situation
            and self.star.task
            and self.star.action
            and self.star.result
        )
        # evidence_files_count is populated by validator (needs FS access).
        return self
