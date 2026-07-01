"""Resume schema — structured resume content (NOT the rendered HTML)."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from pydantic import Field, model_validator

from .base import SchemaBase


# ---------------------------------------------------------------------------
# Section models — a resume is an ordered list of these.
# ---------------------------------------------------------------------------


class HeaderSection(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: Literal["header"] = "header"
    name: str = Field(..., min_length=1)
    role_title: Optional[str] = None
    contact: dict = Field(
        default_factory=dict,
        description="Free-form contact dict; renderer picks what to show.",
    )


class SummarySection(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: Literal["summary"] = "summary"
    content: str = Field(..., min_length=1)


class SkillGroup(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    label: str = Field(..., min_length=1)
    items: List[str] = Field(default_factory=list)


class SkillsSection(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: Literal["skills"] = "skills"
    groups: List[SkillGroup] = Field(default_factory=list)


class ExperienceAchievement(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    text: str = Field(..., min_length=1)
    source_project: Optional[str] = Field(
        default=None,
        description=(
            "Project id (proj-NNN-...) that this bullet is derived from. "
            "Required by evidence validator for entries claiming metrics."
        ),
    )


class ExperienceEntry(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    period: str = Field(..., min_length=1)
    achievements: List[ExperienceAchievement] = Field(default_factory=list)


class ExperienceSection(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: Literal["experience"] = "experience"
    entries: List[ExperienceEntry] = Field(default_factory=list)


class ProjectRefEntry(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    source_project: str = Field(
        ...,
        pattern=r"^proj-\d{3}-[\w\u4e00-\u9fff\-]+$",
    )
    emphasis: Literal["full", "brief"] = "full"


class ProjectsSection(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: Literal["projects"] = "projects"
    entries: List[ProjectRefEntry] = Field(default_factory=list)


ResumeSection = Union[
    HeaderSection,
    SummarySection,
    SkillsSection,
    ExperienceSection,
    ProjectsSection,
]


# ---------------------------------------------------------------------------
# Validation metadata
# ---------------------------------------------------------------------------


class ResumeValidationMeta(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    passed: bool = False
    passed_at: Optional[datetime] = None
    validator_version: Optional[str] = None
    checks: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


class Resume(SchemaBase):
    """Root schema for ``resumes/<jd>/resume-v<N>.yaml``."""

    schema_type: Literal["resume"] = "resume"

    id: str = Field(..., pattern=r"^resume-v\d+$")
    jd_id: str = Field(..., pattern=r"^jd-\d{3}-[\w\u4e00-\u9fff\-]+$")
    created_at: Optional[datetime] = None
    template: str = Field(default="tech-standard", min_length=1)
    locale: str = "zh-CN"

    sections: List[ResumeSection] = Field(default_factory=list)
    validation: ResumeValidationMeta = Field(
        default_factory=ResumeValidationMeta,
        alias="_validation",
    )

    @model_validator(mode="after")
    def _must_have_header_and_at_most_one_of_each(self) -> "Resume":
        counts: Dict[str, int] = {}
        for s in self.sections:
            counts[s.type] = counts.get(s.type, 0) + 1
        if counts.get("header", 0) != 1:
            raise ValueError("resume must contain exactly one 'header' section")
        for key in ("summary", "skills", "experience", "projects"):
            if counts.get(key, 0) > 1:
                raise ValueError(f"resume may contain at most one {key!r} section")
        return self

    def project_refs(self) -> List[str]:
        """Return all project IDs referenced by this resume (dedup)."""
        seen: Dict[str, None] = {}
        for s in self.sections:
            if isinstance(s, ProjectsSection):
                for e in s.entries:
                    seen[e.source_project] = None
            elif isinstance(s, ExperienceSection):
                for entry in s.entries:
                    for a in entry.achievements:
                        if a.source_project:
                            seen[a.source_project] = None
        return list(seen)
