"""Identity: user's basic info + target position."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import EmailStr, Field, HttpUrl, field_validator

from .base import ExperienceLevel, LocalizedString, SchemaBase


class ContactLink(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    type: str = Field(..., description="E.g. github / linkedin / blog / portfolio")
    url: str = Field(..., description="Full URL, including scheme.")

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"contact link URL must start with http(s):// — got {v!r}")
        return v


class Contact(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: List[ContactLink] = Field(default_factory=list)


class TargetPosition(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    role: str = Field(..., min_length=1, description="Target role, free text.")
    industry: str = Field(..., min_length=1)
    experience_level: ExperienceLevel
    preferred_locations: List[str] = Field(default_factory=list)


class Identity(SchemaBase):
    """Root schema for ``profile/identity.yaml``."""

    schema_type: Literal["identity"] = "identity"

    name: LocalizedString
    contact: Contact = Field(default_factory=Contact)
    target: TargetPosition
    locale_preference: str = Field(
        default="zh-CN",
        description="IETF BCP 47 code. Rendering uses this as primary locale.",
    )
    created_at: Optional[datetime] = None
