"""Tests for tools.schemas — Pydantic v2 model validation.

Uses only the exported models. Focuses on:
    * required fields
    * enum / regex constraints
    * cross-field validators
    * schema_version literal enforcement
    * LocalizedString fallback logic
    * legacy experience_level conversion
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tools.schemas import (
    Achievement,
    Contact,
    EvidenceStrength,
    ExperienceLevel,
    Identity,
    JDMeta,
    JDSource,
    JobDescription,
    LocalizedString,
    ProficiencyLevel,
    Project,
    ProjectMeta,
    ProjectPeriod,
    Resume,
    STARStory,
    Skill,
    SkillCategory,
    SkillTree,
    TargetPosition,
)
from tools.schemas.base import SCHEMA_VERSION, SchemaVersionError
from tools.schemas.outcomes import EventType, OutcomeEvent, Outcomes
from tools.schemas.resume import (
    ExperienceAchievement,
    ExperienceEntry,
    ExperienceSection,
    HeaderSection,
    ProjectRefEntry,
    ProjectsSection,
)


# ---------------------------------------------------------------------------
# base / SCHEMA_VERSION
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_current_version_is_two_zero(self):
        assert SCHEMA_VERSION == "2.0"

    def test_schema_version_error_message_includes_migrate_hint(self):
        err = SchemaVersionError("1.0", "2.0", path="foo.yaml")
        s = str(err)
        assert "1.0" in s and "2.0" in s
        assert "resume migrate" in s
        assert "foo.yaml" in s


class TestLocalizedString:
    def test_prefers_zh_when_locale_zh(self):
        ls = LocalizedString(zh="张三", en="Zhang San")
        assert ls.get("zh-CN") == "张三"

    def test_prefers_en_when_locale_en(self):
        ls = LocalizedString(zh="张三", en="Zhang San")
        assert ls.get("en-US") == "Zhang San"

    def test_falls_back_when_primary_missing(self):
        ls = LocalizedString(en="Zhang San")
        assert ls.get("zh-CN") == "Zhang San"

    def test_raises_when_both_missing(self):
        ls = LocalizedString()
        with pytest.raises(ValueError):
            ls.get("zh-CN")


class TestProficiencyLevel:
    def test_ordering(self):
        order = ProficiencyLevel.order()
        assert order[0] == ProficiencyLevel.KNOWN
        assert order[-1] == ProficiencyLevel.EXPERT

    def test_rank_expert_greater_than_known(self):
        assert ProficiencyLevel.EXPERT.rank() > ProficiencyLevel.KNOWN.rank()


class TestExperienceLevel:
    @pytest.mark.parametrize("legacy,expected", [
        ("应届", ExperienceLevel.FRESH),
        ("fresh", ExperienceLevel.FRESH),
        ("1-3年", ExperienceLevel.Y1_3),
        ("3-5年", ExperienceLevel.Y3_5),
        ("3-5y", ExperienceLevel.Y3_5),
        ("5年+", ExperienceLevel.Y5P),
        ("5y+", ExperienceLevel.Y5P),
    ])
    def test_from_legacy_known_values(self, legacy, expected):
        assert ExperienceLevel.from_legacy(legacy) == expected

    def test_from_legacy_unknown_raises(self):
        with pytest.raises(ValueError):
            ExperienceLevel.from_legacy("十年")


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_minimal_valid(self):
        idn = Identity(
            name=LocalizedString(zh="张三"),
            target=TargetPosition(
                role="后端",
                industry="互联网",
                experience_level=ExperienceLevel.Y3_5,
            ),
        )
        assert idn.schema_type == "identity"
        assert idn.locale_preference == "zh-CN"

    def test_rejects_extra_field(self):
        with pytest.raises(ValidationError):
            Identity(
                name=LocalizedString(zh="X"),
                target=TargetPosition(
                    role="X", industry="X",
                    experience_level=ExperienceLevel.FRESH,
                ),
                unknown_field="oops",
            )

    def test_contact_link_requires_http_scheme(self):
        with pytest.raises(ValidationError):
            Contact.model_validate({
                "links": [{"type": "github", "url": "github.com/x"}]
            })


# ---------------------------------------------------------------------------
# skills
# ---------------------------------------------------------------------------


class TestSkillTree:
    def test_duplicate_skill_name_in_same_category_rejected(self):
        with pytest.raises(ValidationError):
            SkillTree(categories=[
                SkillCategory(
                    id="p",
                    label=LocalizedString(zh="p"),
                    skills=[
                        Skill(name="Python", proficiency=ProficiencyLevel.EXPERT),
                        Skill(name="python", proficiency=ProficiencyLevel.KNOWN),
                    ],
                )
            ])

    def test_find_skill_case_insensitive(self):
        tree = SkillTree(categories=[
            SkillCategory(
                id="p",
                label=LocalizedString(zh="p"),
                skills=[Skill(name="Python", proficiency=ProficiencyLevel.EXPERT)],
            )
        ])
        assert tree.find_skill("PYTHON") is not None
        assert tree.find_skill("Go") is None

    def test_all_skills_flattens(self):
        tree = SkillTree(categories=[
            SkillCategory(id="a", label=LocalizedString(zh="A"), skills=[
                Skill(name="X", proficiency=ProficiencyLevel.KNOWN),
                Skill(name="Y", proficiency=ProficiencyLevel.KNOWN),
            ]),
            SkillCategory(id="b", label=LocalizedString(zh="B"), skills=[
                Skill(name="Z", proficiency=ProficiencyLevel.KNOWN),
            ]),
        ])
        assert len(tree.all_skills()) == 3


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------


def _make_project(**overrides):
    base = dict(
        id="proj-001-系统性能优化",
        meta=ProjectMeta(
            name=LocalizedString(zh="系统性能优化"),
            period=ProjectPeriod(start="2024-01", end="2024-06"),
            role="后端",
        ),
        star=STARStory(
            situation="核心系统", task="性能优化", action="加缓存", result="P99 -81%"
        ),
        achievements=[
            Achievement(type="performance", metric="P99", before="800ms", after="150ms", delta="-81%", source="prom"),
        ],
    )
    base.update(overrides)
    return Project(**base)


class TestProject:
    def test_id_pattern_enforced(self):
        with pytest.raises(ValidationError):
            _make_project(id="proj-1-xxx")  # not 3 digits

    def test_star_all_fields_required(self):
        with pytest.raises(ValidationError):
            Project(
                id="proj-001-x",
                meta=ProjectMeta(
                    name=LocalizedString(zh="x"),
                    period=ProjectPeriod(start="2024-01"),
                    role="x",
                ),
                star=STARStory(situation="", task="t", action="a", result="r"),
            )

    def test_verification_score_only_for_code_trace(self):
        with pytest.raises(ValidationError):
            _make_project(verification_score=90)  # default verified_by=dialog

    def test_recompute_sets_quantified_true(self):
        p = _make_project()
        p.recompute()
        assert p.computed.has_quantified_achievement is True
        assert p.computed.has_star_complete is True

    def test_achievement_is_quantified_detects_digits(self):
        a = Achievement(type="x", metric="m", delta="+12pp", source="s")
        assert a.is_quantified is True

        a2 = Achievement(type="x", metric="m", source="s", before="high", after="low")
        assert a2.is_quantified is False


# ---------------------------------------------------------------------------
# jd
# ---------------------------------------------------------------------------


class TestJobDescription:
    def test_minimal_valid(self):
        jd = JobDescription(
            id="jd-001-xx公司后端",
            source=JDSource(type="paste", raw_text="要求 Python 精通"),
            meta=JDMeta(company="XX 公司", role="后端"),
        )
        assert jd.schema_type == "jd"

    def test_id_pattern_enforced(self):
        with pytest.raises(ValidationError):
            JobDescription(
                id="jd-1-x",
                source=JDSource(type="paste", raw_text="x"),
                meta=JDMeta(company="c", role="r"),
            )

    def test_duplicate_requirement_id_rejected(self):
        from tools.schemas.jd import JDRequirement, RequirementPriority
        with pytest.raises(ValidationError):
            JobDescription(
                id="jd-001-x",
                source=JDSource(type="paste", raw_text="x"),
                meta=JDMeta(company="c", role="r"),
                requirements=[
                    JDRequirement(id="req-1", text=LocalizedString(zh="a"), priority=RequirementPriority.MUST_HAVE),
                    JDRequirement(id="req-1", text=LocalizedString(zh="b"), priority=RequirementPriority.MUST_HAVE),
                ],
            )


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


def _make_resume(**overrides):
    base = dict(
        id="resume-v1",
        jd_id="jd-001-xx公司后端",
        sections=[HeaderSection(name="张三")],
    )
    base.update(overrides)
    return Resume(**base)


class TestResume:
    def test_minimal_valid(self):
        r = _make_resume()
        assert r.template == "tech-standard"
        assert r.project_refs() == []

    def test_requires_exactly_one_header(self):
        with pytest.raises(ValidationError):
            Resume(
                id="resume-v1", jd_id="jd-001-x",
                sections=[HeaderSection(name="A"), HeaderSection(name="B")],
            )
        with pytest.raises(ValidationError):
            Resume(id="resume-v1", jd_id="jd-001-x", sections=[])

    def test_project_refs_collects_from_projects_and_experience_sections(self):
        r = _make_resume(sections=[
            HeaderSection(name="张三"),
            ExperienceSection(entries=[
                ExperienceEntry(company="C", role="R", period="p", achievements=[
                    ExperienceAchievement(text="did X", source_project="proj-001-a"),
                ]),
            ]),
            ProjectsSection(entries=[
                ProjectRefEntry(source_project="proj-002-b"),
                ProjectRefEntry(source_project="proj-001-a"),  # dedup
            ]),
        ])
        refs = r.project_refs()
        assert set(refs) == {"proj-001-a", "proj-002-b"}
        assert len(refs) == 2  # deduplicated


# ---------------------------------------------------------------------------
# outcomes
# ---------------------------------------------------------------------------


class TestOutcomes:
    def test_next_event_id_starts_at_001(self):
        o = Outcomes(jd_id="jd-001-x")
        assert o.next_event_id() == "evt-001"

    def test_next_event_id_increments(self):
        o = Outcomes(
            jd_id="jd-001-x",
            events=[
                OutcomeEvent(id="evt-001", timestamp="2026-06-14T09:00:00+08:00", type=EventType.SUBMITTED),
                OutcomeEvent(id="evt-003", timestamp="2026-06-14T10:00:00+08:00", type=EventType.RESPONSE),
            ],
        )
        assert o.next_event_id() == "evt-004"

    def test_duplicate_event_id_rejected(self):
        with pytest.raises(ValidationError):
            Outcomes(
                jd_id="jd-001-x",
                events=[
                    OutcomeEvent(id="evt-001", timestamp="2026-06-14T09:00:00+08:00", type=EventType.SUBMITTED),
                    OutcomeEvent(id="evt-001", timestamp="2026-06-14T10:00:00+08:00", type=EventType.SUBMITTED),
                ],
            )
