"""Skill tree schema."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field, model_validator

from .base import EvidenceStrength, LocalizedString, ProficiencyLevel, SchemaBase


class SkillEvidence(SchemaBase):
    """Concrete evidence that supports a skill claim.

    ``projects`` references project IDs (``proj-NNN-...``) under
    ``profile/projects/``. ``evidence_validator`` verifies each referenced
    project actually exists.
    """

    schema_version: Literal["2.0"] = "2.0"

    projects: List[str] = Field(default_factory=list)
    years_of_use: Optional[float] = Field(default=None, ge=0)
    last_used: Optional[str] = Field(
        default=None,
        description="YYYY-MM or free text like '2024-06'.",
    )
    notes: Optional[str] = None


class Skill(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    name: str = Field(..., min_length=1)
    proficiency: ProficiencyLevel
    evidence_strength: EvidenceStrength = Field(
        default=EvidenceStrength.NONE,
        description=(
            "Computed by evidence_validator based on proficiency + evidence. "
            "User-supplied value will be overwritten."
        ),
    )
    score: Optional[int] = Field(default=None, ge=1, le=10, description="Self-rating 1-10.")
    evidence: SkillEvidence = Field(default_factory=SkillEvidence)
    keywords_zh: List[str] = Field(default_factory=list)
    keywords_en: List[str] = Field(default_factory=list)


class SkillCategory(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    id: str = Field(..., min_length=1, description="Machine id, e.g. 'programming'.")
    label: LocalizedString
    skills: List[Skill] = Field(default_factory=list)


class SkillTree(SchemaBase):
    """Root schema for ``profile/skills/data.yaml``."""

    schema_type: Literal["skill_tree"] = "skill_tree"

    categories: List[SkillCategory] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_skill_names_per_category(self) -> "SkillTree":
        for cat in self.categories:
            seen: set[str] = set()
            for s in cat.skills:
                key = s.name.lower()
                if key in seen:
                    raise ValueError(
                        f"duplicate skill {s.name!r} in category {cat.id!r}"
                    )
                seen.add(key)
        return self

    def all_skills(self) -> List[Skill]:
        return [s for c in self.categories for s in c.skills]

    def find_skill(self, name: str) -> Optional[Skill]:
        needle = name.lower()
        for s in self.all_skills():
            if s.name.lower() == needle:
                return s
        return None
