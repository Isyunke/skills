"""Tests for tools.evidence_validator — the three-principle enforcer.

Uses a fixture that assembles a small in-memory KB on disk, then runs the
validator and inspects the ``ValidationResult``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import io_utils
from tools.evidence_validator import (
    Principle,
    Severity,
    ValidationResult,
    compute_evidence_strength,
    render_result_text,
    validate_project,
)
from tools.schemas import EvidenceStrength, ProficiencyLevel
from tools.schemas.project import (
    Achievement,
    Project,
    ProjectMeta,
    ProjectPeriod,
    STARStory,
    VerificationMethod,
)
from tools.schemas.base import LocalizedString


# ---------------------------------------------------------------------------
# Fixtures — small KB scaffolding helper
# ---------------------------------------------------------------------------


def _write_project(
    root: Path,
    *,
    pid: str,
    quantified: bool = True,
    achievements: int = 1,
) -> None:
    achs = []
    for i in range(achievements):
        achs.append({
            "schema_version": "2.0",
            "type": "performance",
            "metric": f"metric-{i}",
            "before": "800ms" if quantified else "high",
            "after": "150ms" if quantified else "low",
            "delta": "-81%" if quantified else None,
            "source": "prom-dashboard",
        })
    proj_dir = root / "profile" / "projects" / pid
    io_utils.dump_yaml(proj_dir / "data.yaml", {
        "schema_version": "2.0",
        "schema_type": "project",
        "id": pid,
        "meta": {
            "schema_version": "2.0",
            "name": {"zh": pid},
            "period": {"schema_version": "2.0", "start": "2024-01", "end": "2024-06"},
            "role": "后端",
        },
        "star": {
            "schema_version": "2.0",
            "situation": "s", "task": "t", "action": "a", "result": "r",
        },
        "achievements": achs,
    })


def _write_skill_tree(root: Path, skills: list[dict]) -> None:
    """skills: list of {"name": str, "proficiency": str, "evidence_projects": [ids]}"""
    io_utils.dump_yaml(root / "profile" / "skills" / "data.yaml", {
        "schema_version": "2.0",
        "schema_type": "skill_tree",
        "categories": [{
            "schema_version": "2.0",
            "id": "programming",
            "label": {"zh": "编程"},
            "skills": [
                {
                    "schema_version": "2.0",
                    "name": s["name"],
                    "proficiency": s["proficiency"],
                    "evidence_strength": "none",
                    "evidence": {
                        "schema_version": "2.0",
                        "projects": s.get("evidence_projects", []),
                    },
                }
                for s in skills
            ],
        }],
    })


def _write_jd(root: Path, jd_id: str) -> None:
    io_utils.dump_yaml(root / "resumes" / jd_id / "jd.yaml", {
        "schema_version": "2.0",
        "schema_type": "jd",
        "id": jd_id,
        "source": {"schema_version": "2.0", "type": "paste", "raw_text": "raw"},
        "meta": {"schema_version": "2.0", "company": "XX", "role": "后端"},
    })


def _write_resume(root: Path, jd_id: str, project_refs: list[str] | None = None) -> None:
    sections = [{"schema_version": "2.0", "type": "header", "name": "张三"}]
    if project_refs:
        sections.append({
            "schema_version": "2.0",
            "type": "projects",
            "entries": [
                {"schema_version": "2.0", "source_project": p, "emphasis": "full"}
                for p in project_refs
            ],
        })
    io_utils.dump_yaml(root / "resumes" / jd_id / "resume-v1.yaml", {
        "schema_version": "2.0",
        "schema_type": "resume",
        "id": "resume-v1",
        "jd_id": jd_id,
        "template": "tech-standard",
        "locale": "zh-CN",
        "sections": sections,
    })


# ---------------------------------------------------------------------------
# Empty project — vacuously passes
# ---------------------------------------------------------------------------


class TestEmptyProject:
    def test_empty_repo_passes_all_principles(self, tmp_path: Path):
        result = validate_project(tmp_path)
        assert result.passed
        assert result.checked_files == 0
        assert result.principle_summary == {
            "truth_first": "pass",
            "evidence_chain": "pass",
            "targeted_for_jd": "pass",
        }


# ---------------------------------------------------------------------------
# truth_first
# ---------------------------------------------------------------------------


class TestTruthFirst:
    def test_estimate_source_is_error(self, tmp_path: Path):
        _write_project(tmp_path, pid="proj-001-a")
        # patch source to "estimate"
        yaml_path = tmp_path / "profile" / "projects" / "proj-001-a" / "data.yaml"
        raw = io_utils.load_yaml(yaml_path)
        raw["achievements"][0]["source"] = "estimate"
        io_utils.dump_yaml(yaml_path, raw)

        result = validate_project(tmp_path, principles=[Principle.TRUTH_FIRST])
        errs = result.errors()
        assert len(errs) == 1
        assert errs[0].principle == Principle.TRUTH_FIRST
        assert "estimate" in errs[0].message_zh or "estimate" in errs[0].message_en
        assert result.principle_summary["truth_first"] == "fail"

    def test_resume_referencing_missing_project_errors(self, tmp_path: Path):
        _write_jd(tmp_path, "jd-001-x")
        _write_resume(tmp_path, "jd-001-x", project_refs=["proj-999-ghost"])
        result = validate_project(tmp_path, principles=[Principle.TRUTH_FIRST])
        errs = [e for e in result.errors() if "ghost" in e.location]
        assert errs, "expected an error citing the missing project"
        assert errs[0].fix  # every violation must ship a fix hint


# ---------------------------------------------------------------------------
# evidence_chain
# ---------------------------------------------------------------------------


class TestEvidenceChain:
    def test_expert_without_projects_blocks(self, tmp_path: Path):
        _write_skill_tree(tmp_path, [
            {"name": "Python", "proficiency": "expert", "evidence_projects": []},
        ])
        result = validate_project(tmp_path, principles=[Principle.EVIDENCE_CHAIN])
        assert not result.passed
        assert any(v.principle == Principle.EVIDENCE_CHAIN for v in result.errors())

    def test_expert_with_two_projects_but_no_quantification_blocks(self, tmp_path: Path):
        _write_project(tmp_path, pid="proj-001-a", quantified=False)
        _write_project(tmp_path, pid="proj-002-b", quantified=False)
        _write_skill_tree(tmp_path, [
            {"name": "Python", "proficiency": "expert",
             "evidence_projects": ["proj-001-a", "proj-002-b"]},
        ])
        result = validate_project(tmp_path, principles=[Principle.EVIDENCE_CHAIN])
        assert not result.passed
        msgs = " ".join(v.message_zh for v in result.errors())
        assert "expert" in msgs.lower() or "量化" in msgs

    def test_expert_with_two_projects_and_quantification_passes(self, tmp_path: Path):
        _write_project(tmp_path, pid="proj-001-a", quantified=True)
        _write_project(tmp_path, pid="proj-002-b", quantified=True)
        _write_skill_tree(tmp_path, [
            {"name": "Python", "proficiency": "expert",
             "evidence_projects": ["proj-001-a", "proj-002-b"]},
        ])
        result = validate_project(tmp_path, principles=[Principle.EVIDENCE_CHAIN])
        assert result.passed, [v.message_zh for v in result.errors()]

    def test_proficient_needs_one_project(self, tmp_path: Path):
        _write_skill_tree(tmp_path, [
            {"name": "Java", "proficiency": "proficient", "evidence_projects": []},
        ])
        result = validate_project(tmp_path, principles=[Principle.EVIDENCE_CHAIN])
        assert not result.passed

    def test_known_passes_with_no_evidence(self, tmp_path: Path):
        _write_skill_tree(tmp_path, [
            {"name": "Go", "proficiency": "known", "evidence_projects": []},
        ])
        result = validate_project(tmp_path, principles=[Principle.EVIDENCE_CHAIN])
        assert result.passed

    def test_unknown_project_reference_flagged(self, tmp_path: Path):
        _write_project(tmp_path, pid="proj-001-a", quantified=True)
        _write_skill_tree(tmp_path, [
            {"name": "Python", "proficiency": "proficient",
             "evidence_projects": ["proj-001-a", "proj-999-missing"]},
        ])
        result = validate_project(tmp_path, principles=[Principle.EVIDENCE_CHAIN])
        assert any(
            "proj-999-missing" in v.message_zh or "proj-999-missing" in v.message_en
            for v in result.errors()
        )


# ---------------------------------------------------------------------------
# targeted_for_jd
# ---------------------------------------------------------------------------


class TestTargetedForJd:
    def test_resume_without_matching_jd_errors(self, tmp_path: Path):
        # write a resume but no jd.yaml
        _write_resume(tmp_path, "jd-001-missing")
        result = validate_project(tmp_path, principles=[Principle.TARGETED_FOR_JD])
        assert not result.passed
        assert any("jd_id" in v.location for v in result.errors())

    def test_resume_with_matching_jd_passes(self, tmp_path: Path):
        _write_jd(tmp_path, "jd-001-ok")
        _write_resume(tmp_path, "jd-001-ok")
        result = validate_project(tmp_path, principles=[Principle.TARGETED_FOR_JD])
        assert result.passed


# ---------------------------------------------------------------------------
# compute_evidence_strength
# ---------------------------------------------------------------------------


def _proj_stub(quantified: bool) -> Project:
    return Project(
        id="proj-001-a",
        verified_by=VerificationMethod.DIALOG,
        meta=ProjectMeta(
            name=LocalizedString(zh="x"),
            period=ProjectPeriod(start="2024-01", end="2024-06"),
            role="x",
        ),
        star=STARStory(situation="s", task="t", action="a", result="r"),
        achievements=[
            Achievement(
                type="x", metric="m",
                before=("800ms" if quantified else "high"),
                after=("150ms" if quantified else "low"),
                delta=("-81%" if quantified else None),
                source="s",
            )
        ],
    )


class TestComputeEvidenceStrength:
    def test_no_projects_none(self):
        assert compute_evidence_strength(ProficiencyLevel.EXPERT, []) == EvidenceStrength.NONE

    def test_expert_with_2_projects_and_quant_strong(self):
        strength = compute_evidence_strength(
            ProficiencyLevel.EXPERT,
            [_proj_stub(True), _proj_stub(True)],
        )
        assert strength == EvidenceStrength.STRONG

    def test_expert_with_2_projects_no_quant_weak(self):
        strength = compute_evidence_strength(
            ProficiencyLevel.EXPERT,
            [_proj_stub(False), _proj_stub(False)],
        )
        assert strength == EvidenceStrength.WEAK

    def test_proficient_with_1_quant_project_strong(self):
        strength = compute_evidence_strength(
            ProficiencyLevel.PROFICIENT, [_proj_stub(True)]
        )
        assert strength == EvidenceStrength.STRONG

    def test_known_with_project_weak(self):
        strength = compute_evidence_strength(
            ProficiencyLevel.KNOWN, [_proj_stub(True)]
        )
        assert strength == EvidenceStrength.WEAK


# ---------------------------------------------------------------------------
# render / CLI
# ---------------------------------------------------------------------------


class TestReportRendering:
    def test_render_result_text_has_headline_and_status(self, tmp_path: Path):
        result = validate_project(tmp_path)
        text = render_result_text(result)
        assert "Evidence Validation Report" in text
        # empty repo -> all pass -> 通过
        assert "通过" in text or "All principles" in text

    def test_render_result_text_shows_fix_for_violation(self, tmp_path: Path):
        _write_skill_tree(tmp_path, [
            {"name": "Python", "proficiency": "expert", "evidence_projects": []},
        ])
        result = validate_project(tmp_path)
        text = render_result_text(result)
        assert "how:" in text
        assert "Python" in text
