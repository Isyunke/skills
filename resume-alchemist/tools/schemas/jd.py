"""Job Description schema."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import Field, model_validator

from .base import LocalizedString, SchemaBase


class RequirementPriority(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    BONUS = "bonus"


class JDSource(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: Literal["paste", "url", "file"]
    raw_text: str = Field(..., min_length=1)
    url: Optional[str] = None


class JDMeta(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    salary_range: Optional[str] = None
    location: Optional[str] = None
    level: Optional[str] = None


class JDRequirement(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    id: str = Field(..., pattern=r"^req-\d+$")
    text: LocalizedString
    priority: RequirementPriority
    keywords: List[str] = Field(default_factory=list)
    category: Optional[str] = None


class ExtractedKeyword(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    term: str = Field(..., min_length=1)
    weight: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(
        ...,
        description="ID of the requirement (e.g. 'req-1') this keyword came from.",
    )


class ExtractedKeywords(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    all: List[ExtractedKeyword] = Field(default_factory=list)
    top_n: int = Field(default=10, ge=1)


class JobDescription(SchemaBase):
    """Root schema for ``resumes/<jd>/jd.yaml``."""

    schema_type: Literal["jd"] = "jd"

    id: str = Field(..., pattern=r"^jd-\d{3}-[\w\u4e00-\u9fff\-]+$")
    created_at: Optional[datetime] = None
    source: JDSource
    meta: JDMeta
    requirements: List[JDRequirement] = Field(default_factory=list)
    extracted_keywords: ExtractedKeywords = Field(default_factory=ExtractedKeywords)

    @model_validator(mode="after")
    def _unique_requirement_ids(self) -> "JobDescription":
        seen: set[str] = set()
        for r in self.requirements:
            if r.id in seen:
                raise ValueError(f"duplicate requirement id {r.id!r}")
            seen.add(r.id)
        return self
