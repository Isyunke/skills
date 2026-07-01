"""Shared enums / base types / schema version constant."""
from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION: Literal["2.0"] = "2.0"


class SchemaVersionError(ValueError):
    """Raised when a YAML file's ``schema_version`` does not match ``SCHEMA_VERSION``.

    Consumers should catch this and route the file through ``tools.migrate``.
    """

    def __init__(self, found: str, expected: str = SCHEMA_VERSION, path: Optional[str] = None):
        self.found = found
        self.expected = expected
        self.path = path
        loc = f" (in {path})" if path else ""
        super().__init__(
            f"schema_version mismatch{loc}: found {found!r}, expected {expected!r}. "
            f"Run `resume migrate` to upgrade."
        )


class SchemaBase(BaseModel):
    """Base for all top-level schema roots.

    Subclasses set ``schema_type`` via a ``Literal`` and inherit strict
    validation defaults.
    """

    model_config = ConfigDict(
        extra="forbid",           # unknown keys are errors, not silently dropped
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    schema_version: Literal["2.0"] = Field(
        default=SCHEMA_VERSION,
        description="Schema major.minor version. Must match SCHEMA_VERSION.",
    )


class LocalizedString(BaseModel):
    """A string with per-locale variants.

    At least one of ``zh`` / ``en`` must be present. Rendering code should
    fall back in the order dictated by ``.resume-config.yaml``.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    zh: Optional[str] = None
    en: Optional[str] = None

    def get(self, locale: str = "zh-CN", *, fallback: str = "en-US") -> str:
        """Return the best available variant for ``locale``.

        Raises ValueError if no variant is available at all.
        """
        primary = "zh" if locale.startswith("zh") else "en"
        secondary = "en" if primary == "zh" else "zh"
        value = getattr(self, primary) or getattr(self, secondary)
        if value is None:
            raise ValueError("LocalizedString has neither zh nor en set")
        return value


class ProficiencyLevel(str, Enum):
    """User's self-declared proficiency for a skill.

    Order matters: ``expert > proficient > known``. The evidence validator
    enforces different evidence thresholds per level.
    """

    KNOWN = "known"           # 了解
    PROFICIENT = "proficient" # 熟练
    EXPERT = "expert"         # 精通

    @classmethod
    def order(cls) -> List["ProficiencyLevel"]:
        return [cls.KNOWN, cls.PROFICIENT, cls.EXPERT]

    def rank(self) -> int:
        return self.order().index(self)


class EvidenceStrength(str, Enum):
    """Computed strength of the evidence backing a skill claim.

    NEVER user-writable — always derived by ``evidence_validator``.
    """

    NONE = "none"
    WEAK = "weak"
    STRONG = "strong"


class ExperienceLevel(str, Enum):
    FRESH = "fresh"     # 应届
    Y1_3 = "1-3y"
    Y3_5 = "3-5y"
    Y5P = "5y+"

    @classmethod
    def from_legacy(cls, s: str) -> "ExperienceLevel":
        """Map v1 free-text values (e.g. '应届', '3-5年') to v2 enum."""
        s = s.strip()
        mapping = {
            "应届": cls.FRESH,
            "fresh": cls.FRESH,
            "1-3年": cls.Y1_3,
            "1-3y": cls.Y1_3,
            "3-5年": cls.Y3_5,
            "3-5y": cls.Y3_5,
            "5年+": cls.Y5P,
            "5+": cls.Y5P,
            "5y+": cls.Y5P,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"unknown experience level: {s!r}")
