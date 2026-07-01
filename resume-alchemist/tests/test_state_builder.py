"""Tests for tools.state_builder — deriving .resume-state.json from KB."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import io_utils
from tools.schemas import ExperienceLevel
from tools.state_builder import build_state, refresh_state_file, STATE_FILENAME


# ---------------------------------------------------------------------------
# Helpers (mirrors those in test_evidence_validator, but kept local for clarity)
# ---------------------------------------------------------------------------


def _write_identity(root: Path, role: str = "后端", industry: str = "互联网",
                    xp: str = "3-5y") -> None:
    io_utils.dump_yaml(root / "profile" / "identity.yaml", {
        "schema_version": "2.0",
        "schema_type": "identity",
        "name": {"zh": "张三"},
        "contact": {"schema_version": "2.0"},
        "target": {
            "schema_version": "2.0",
            "role": role,
            "industry": industry,
            "experience_level": xp,
        },
        "locale_preference": "zh-CN",
    })


def _write_project(root: Path, pid: str, verified_by: str = "dialog") -> None:
    payload = {
        "schema_version": "2.0",
        "schema_type": "project",
        "id": pid,
        "verified_by": verified_by,
        "meta": {
            "schema_version": "2.0",
            "name": {"zh": pid},
            "period": {"schema_version": "2.0", "start": "2024-01", "end": "2024-06"},
            "role": "后端",
        },
        "star": {"schema_version": "2.0", "situation": "s", "task": "t", "action": "a", "result": "r"},
        "achievements": [{
            "schema_version": "2.0",
            "type": "performance",
            "metric": "p99",
            "before": "800ms",
            "after": "150ms",
            "delta": "-81%",
            "source": "prom",
        }],
    }
    if verified_by == "code_trace":
        payload["verification_score"] = 92
    io_utils.dump_yaml(root / "profile" / "projects" / pid / "data.yaml", payload)


def _write_jd(root: Path, jd_id: str) -> None:
    io_utils.dump_yaml(root / "resumes" / jd_id / "jd.yaml", {
        "schema_version": "2.0",
        "schema_type": "jd",
        "id": jd_id,
        "source": {"schema_version": "2.0", "type": "paste", "raw_text": "raw"},
        "meta": {"schema_version": "2.0", "company": "XX", "role": "后端"},
    })


def _write_resume(root: Path, jd_id: str, v: int = 1) -> None:
    io_utils.dump_yaml(root / "resumes" / jd_id / f"resume-v{v}.yaml", {
        "schema_version": "2.0",
        "schema_type": "resume",
        "id": f"resume-v{v}",
        "jd_id": jd_id,
        "template": "tech-standard",
        "locale": "zh-CN",
        "sections": [{"schema_version": "2.0", "type": "header", "name": "张三"}],
    })


def _write_outcomes(root: Path, jd_id: str, event_count: int = 0) -> None:
    events = []
    for i in range(1, event_count + 1):
        events.append({
            "schema_version": "2.0",
            "id": f"evt-{i:03d}",
            "timestamp": "2026-06-14T09:00:00+08:00",
            "type": "submitted",
            "detail": {},
        })
    io_utils.dump_yaml(root / "resumes" / jd_id / "outcomes.yaml", {
        "schema_version": "2.0",
        "schema_type": "outcomes",
        "jd_id": jd_id,
        "events": events,
    })


def _write_skills(root: Path, count: int = 2) -> None:
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
                    "name": f"Skill-{i}",
                    "proficiency": "known",
                    "evidence_strength": "none",
                    "evidence": {"schema_version": "2.0"},
                }
                for i in range(count)
            ],
        }],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildState:
    def test_empty_project_yields_zero_counts(self, tmp_path: Path):
        s = build_state(tmp_path)
        assert s.counts.projects == 0
        assert s.counts.jds == 0
        assert s.counts.resumes == 0
        assert s.active_jd_id is None
        assert s.rebuilt_at is not None

    def test_reads_identity_fields(self, tmp_path: Path):
        _write_identity(tmp_path, role="全栈", industry="金融", xp="1-3y")
        s = build_state(tmp_path)
        assert s.target_role == "全栈"
        assert s.target_industry == "金融"
        assert s.experience_level == ExperienceLevel.Y1_3

    def test_counts_projects_and_verified(self, tmp_path: Path):
        _write_project(tmp_path, "proj-001-a")
        _write_project(tmp_path, "proj-002-b", verified_by="code_trace")
        _write_project(tmp_path, "proj-003-c", verified_by="code_trace")
        s = build_state(tmp_path)
        assert s.counts.projects == 3
        assert s.counts.verified_projects == 2

    def test_counts_jds_and_resumes_and_outcomes_events(self, tmp_path: Path):
        _write_jd(tmp_path, "jd-001-x")
        _write_jd(tmp_path, "jd-002-y")
        _write_resume(tmp_path, "jd-001-x", v=1)
        _write_resume(tmp_path, "jd-001-x", v=2)
        _write_resume(tmp_path, "jd-002-y", v=1)
        _write_outcomes(tmp_path, "jd-001-x", event_count=3)
        _write_outcomes(tmp_path, "jd-002-y", event_count=1)
        s = build_state(tmp_path)
        assert s.counts.jds == 2
        assert s.counts.resumes == 3
        assert s.counts.outcomes_events == 4

    def test_counts_skills(self, tmp_path: Path):
        _write_skills(tmp_path, count=4)
        s = build_state(tmp_path)
        assert s.counts.skills == 4

    def test_active_jd_defaults_to_latest_by_id(self, tmp_path: Path):
        _write_jd(tmp_path, "jd-001-a")
        _write_jd(tmp_path, "jd-005-b")
        _write_jd(tmp_path, "jd-003-c")
        s = build_state(tmp_path)
        assert s.active_jd_id == "jd-005-b"

    def test_active_jd_preserved_from_existing_state(self, tmp_path: Path):
        _write_jd(tmp_path, "jd-001-a")
        _write_jd(tmp_path, "jd-005-b")
        # Prior state file pins jd-001
        io_utils.dump_json(tmp_path / STATE_FILENAME, {
            "active_jd_id": "jd-001-a",
        })
        s = build_state(tmp_path)
        assert s.active_jd_id == "jd-001-a"

    def test_active_jd_ignored_if_no_longer_exists(self, tmp_path: Path):
        _write_jd(tmp_path, "jd-005-b")
        io_utils.dump_json(tmp_path / STATE_FILENAME, {
            "active_jd_id": "jd-999-gone",
        })
        s = build_state(tmp_path)
        assert s.active_jd_id == "jd-005-b"

    def test_broken_yaml_is_ignored_not_crashing(self, tmp_path: Path):
        (tmp_path / "profile" / "projects" / "proj-001-bad").mkdir(parents=True)
        (tmp_path / "profile" / "projects" / "proj-001-bad" / "data.yaml").write_text(
            ": not valid ::", encoding="utf-8"
        )
        # Should not raise
        s = build_state(tmp_path)
        assert s.counts.projects == 0

    def test_initialized_at_preserved_from_existing_state(self, tmp_path: Path):
        prior_iso = "2025-01-01T00:00:00+00:00"
        io_utils.dump_json(tmp_path / STATE_FILENAME, {"initialized_at": prior_iso})
        s = build_state(tmp_path)
        assert s.initialized_at.isoformat().startswith("2025-01-01")


class TestRefreshStateFile:
    def test_writes_and_returns_path(self, tmp_path: Path):
        _write_identity(tmp_path)
        _write_project(tmp_path, "proj-001-a")
        path = refresh_state_file(tmp_path)
        assert path.is_file()
        raw = io_utils.load_json(path)
        assert raw["target_role"] == "后端"
        assert raw["counts"]["projects"] == 1
