"""Outcomes schema — append-only event log for one JD."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import Field, model_validator

from .base import SchemaBase


class EventType(str, Enum):
    SUBMITTED = "submitted"
    RESPONSE = "response"
    INTERVIEW = "interview"
    PAUSE = "pause"
    RESUME_AFTER_PAUSE = "resume_after_pause"
    OFFER = "offer"
    FINAL_RESULT = "final_result"
    USER_NOTE = "user_note"


class OutcomeEvent(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    id: str = Field(..., pattern=r"^evt-\d+$")
    timestamp: datetime
    type: EventType
    detail: dict = Field(default_factory=dict, description="Free-form; per event-type shape.")


class _OutcomesComputed(SchemaBase):
    schema_version: Literal["2.0"] = "2.0"

    total_days_to_close: Optional[int] = None
    rounds_passed: int = 0
    weak_spots: List[str] = Field(default_factory=list)


class Outcomes(SchemaBase):
    """Root schema for ``resumes/<jd>/outcomes.yaml``."""

    schema_type: Literal["outcomes"] = "outcomes"

    jd_id: str = Field(..., pattern=r"^jd-\d{3}-[\w\u4e00-\u9fff\-]+$")
    resume_used: Optional[str] = None
    events: List[OutcomeEvent] = Field(default_factory=list)
    computed: _OutcomesComputed = Field(
        default_factory=_OutcomesComputed,
        alias="_computed",
    )

    @model_validator(mode="after")
    def _monotonic_event_ids(self) -> "Outcomes":
        seen: set[str] = set()
        for e in self.events:
            if e.id in seen:
                raise ValueError(f"duplicate event id {e.id!r}")
            seen.add(e.id)
        return self

    def next_event_id(self) -> str:
        """Return the next sequential ``evt-N`` id."""
        max_n = 0
        for e in self.events:
            try:
                n = int(e.id.split("-", 1)[1])
                max_n = max(max_n, n)
            except (IndexError, ValueError):
                pass
        return f"evt-{max_n + 1:03d}"
