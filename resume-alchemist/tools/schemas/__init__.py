"""Pydantic v2 schema for Resume Alchemist v2 knowledge base.

Every YAML file under a user's resume project is validated against one of
these models. Schema evolution is controlled via the shared ``SCHEMA_VERSION``
constant; breaking changes MUST bump the major version and provide a
migration entry in ``migrations/registry.md``.
"""
from __future__ import annotations

from .base import (
    SCHEMA_VERSION,
    LocalizedString,
    ProficiencyLevel,
    EvidenceStrength,
    ExperienceLevel,
    SchemaBase,
    SchemaVersionError,
)
from .identity import Identity, Contact, TargetPosition, ContactLink
from .skills import SkillTree, SkillCategory, Skill, SkillEvidence
from .project import (
    Project,
    ProjectMeta,
    ProjectPeriod,
    STARStory,
    TechStack,
    SkillUsage,
    Achievement,
    InterviewPrep,
    ProjectLink,
    VerificationMethod,
)
from .jd import (
    JobDescription,
    JDMeta,
    JDSource,
    JDRequirement,
    RequirementPriority,
    ExtractedKeyword,
    ExtractedKeywords,
)
from .resume import (
    Resume,
    ResumeSection,
    HeaderSection,
    SummarySection,
    SkillsSection,
    SkillGroup,
    ExperienceSection,
    ExperienceEntry,
    ExperienceAchievement,
    ProjectsSection,
    ProjectRefEntry,
    ResumeValidationMeta,
)
from .outcomes import Outcomes, OutcomeEvent, EventType
from .state import ResumeState, StateCounts, StateTimestamps

__all__ = [
    # base
    "SCHEMA_VERSION",
    "LocalizedString",
    "ProficiencyLevel",
    "EvidenceStrength",
    "ExperienceLevel",
    "SchemaBase",
    "SchemaVersionError",
    # identity
    "Identity",
    "Contact",
    "TargetPosition",
    "ContactLink",
    # skills
    "SkillTree",
    "SkillCategory",
    "Skill",
    "SkillEvidence",
    # project
    "Project",
    "ProjectMeta",
    "ProjectPeriod",
    "STARStory",
    "TechStack",
    "SkillUsage",
    "Achievement",
    "InterviewPrep",
    "ProjectLink",
    "VerificationMethod",
    # jd
    "JobDescription",
    "JDMeta",
    "JDSource",
    "JDRequirement",
    "RequirementPriority",
    "ExtractedKeyword",
    "ExtractedKeywords",
    # resume
    "Resume",
    "ResumeSection",
    "HeaderSection",
    "SummarySection",
    "SkillsSection",
    "SkillGroup",
    "ExperienceSection",
    "ExperienceEntry",
    "ExperienceAchievement",
    "ProjectsSection",
    "ProjectRefEntry",
    "ResumeValidationMeta",
    # outcomes
    "Outcomes",
    "OutcomeEvent",
    "EventType",
    # state
    "ResumeState",
    "StateCounts",
    "StateTimestamps",
]
