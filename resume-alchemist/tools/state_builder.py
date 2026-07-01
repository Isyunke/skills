"""State builder — derive ``.resume-state.json`` from the KB.

In v2, ``.resume-state.json`` is a *derived cache*, not the source of
truth. It is rebuilt whenever any consumer (CLI, MCP tool, status skill)
needs a fresh snapshot.

If the file already exists from v1, its `initialized_at` timestamp is
preserved so long-lived install signatures survive migration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from .io_utils import dump_json, load_json, load_yaml
from .schemas import (
    ExperienceLevel,
    JobDescription,
    Outcomes,
    Project,
    ResumeState,
    SkillTree,
    StateCounts,
    StateTimestamps,
)
from .schemas.base import SchemaVersionError

STATE_FILENAME = ".resume-state.json"


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _safe_load_yaml(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        return load_yaml(path, check_schema_version=False)
    except Exception:
        return None


def _load_existing_state(state_path: Path) -> Optional[dict]:
    if not state_path.is_file():
        return None
    try:
        return load_json(state_path)
    except Exception:
        return None


def _collect_projects(root: Path) -> List[Project]:
    projects_dir = root / "profile" / "projects"
    if not projects_dir.is_dir():
        return []
    out: List[Project] = []
    for sub in sorted(projects_dir.iterdir()):
        data_yaml = sub / "data.yaml"
        if not data_yaml.is_file():
            continue
        raw = _safe_load_yaml(data_yaml)
        if raw is None:
            continue
        try:
            out.append(Project.model_validate(raw))
        except (ValidationError, SchemaVersionError):
            # We tolerate broken projects here — evidence_validator is the
            # component that reports about them.
            pass
    return out


def _collect_jds_and_outcomes(root: Path):
    """Return (jd_list, outcomes_list). Errors are tolerated (see comment above)."""
    resumes_dir = root / "resumes"
    jds: List[JobDescription] = []
    outcomes: List[Outcomes] = []
    resume_count = 0
    if not resumes_dir.is_dir():
        return jds, outcomes, resume_count
    for jd_dir in sorted(resumes_dir.iterdir()):
        if not jd_dir.is_dir():
            continue
        raw_jd = _safe_load_yaml(jd_dir / "jd.yaml")
        if raw_jd is not None:
            try:
                jds.append(JobDescription.model_validate(raw_jd))
            except (ValidationError, SchemaVersionError):
                pass
        raw_out = _safe_load_yaml(jd_dir / "outcomes.yaml")
        if raw_out is not None:
            try:
                outcomes.append(Outcomes.model_validate(raw_out))
            except (ValidationError, SchemaVersionError):
                pass
        resume_count += len(list(jd_dir.glob("resume-v*.yaml")))
    return jds, outcomes, resume_count


def _load_skill_tree(root: Path) -> Optional[SkillTree]:
    raw = _safe_load_yaml(root / "profile" / "skills" / "data.yaml")
    if raw is None:
        return None
    try:
        return SkillTree.model_validate(raw)
    except (ValidationError, SchemaVersionError):
        return None


def _identity_target(root: Path):
    """Return (target_role, target_industry, experience_level) if identity.yaml exists."""
    raw = _safe_load_yaml(root / "profile" / "identity.yaml")
    if raw is None:
        return None, None, None
    target = raw.get("target") or {}
    role = target.get("role")
    industry = target.get("industry")
    xp_raw = target.get("experience_level")
    xp: Optional[ExperienceLevel] = None
    if xp_raw is not None:
        try:
            xp = ExperienceLevel(xp_raw)
        except ValueError:
            try:
                xp = ExperienceLevel.from_legacy(str(xp_raw))
            except ValueError:
                xp = None
    return role, industry, xp


def _detect_active_jd(existing: Optional[dict], jds: List[JobDescription]) -> Optional[str]:
    """Prefer prior ``active_jd_id`` if it still exists; else the most recent JD."""
    if existing:
        prior = existing.get("active_jd_id")
        if prior and any(jd.id == prior for jd in jds):
            return prior
    if not jds:
        return None
    # No created_at guarantee — sort by id (which is prefixed by NNN sequence).
    return sorted(jds, key=lambda j: j.id, reverse=True)[0].id


def build_state(project_root: Path | str) -> ResumeState:
    """Assemble a fresh :class:`ResumeState` from the KB."""
    root = Path(project_root)
    state_path = root / STATE_FILENAME
    existing = _load_existing_state(state_path)

    skill_tree = _load_skill_tree(root)
    projects = _collect_projects(root)
    jds, outcomes, resume_count = _collect_jds_and_outcomes(root)
    role, industry, xp = _identity_target(root)

    counts = StateCounts(
        projects=len(projects),
        skills=len(skill_tree.all_skills()) if skill_tree else 0,
        jds=len(jds),
        resumes=resume_count,
        verified_projects=sum(1 for p in projects if p.verified_by.value == "code_trace"),
        outcomes_events=sum(len(o.events) for o in outcomes),
    )

    timestamps = StateTimestamps()  # v2 P0: not yet wired to skill hooks

    initialized_at: Optional[datetime] = None
    if existing and existing.get("initialized_at"):
        try:
            initialized_at = datetime.fromisoformat(existing["initialized_at"])
        except (TypeError, ValueError):
            initialized_at = None
    if initialized_at is None:
        initialized_at = _now()

    return ResumeState(
        target_role=role or (existing.get("target_role") if existing else None),
        target_industry=industry or (existing.get("target_industry") if existing else None),
        experience_level=xp,
        active_jd_id=_detect_active_jd(existing, jds),
        pending_learning=list((existing or {}).get("pending_learning") or []),
        counts=counts,
        timestamps=timestamps,
        initialized_at=initialized_at,
        rebuilt_at=_now(),
    )


def refresh_state_file(project_root: Path | str) -> Path:
    """Rebuild ``.resume-state.json`` and write it atomically. Returns the path."""
    root = Path(project_root)
    state = build_state(root)
    state_path = root / STATE_FILENAME
    dump_json(state_path, state.model_dump(mode="json"))
    return state_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json as _json

    p = argparse.ArgumentParser(
        prog="resume-state-builder",
        description="Rebuild .resume-state.json from the current KB.",
    )
    p.add_argument("--project-root", default=".")
    p.add_argument("--write", action="store_true", help="Write to disk (default: dry-run).")
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = p.parse_args(argv)

    root = Path(args.project_root).resolve()
    state = build_state(root)
    payload = state.model_dump(mode="json")

    if args.write:
        refresh_state_file(root)

    if args.json:
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("📊 Rebuilt state:")
        print(f"  target_role:      {state.target_role}")
        print(f"  target_industry:  {state.target_industry}")
        print(f"  experience_level: {state.experience_level}")
        print(f"  active_jd_id:     {state.active_jd_id}")
        print(f"  counts:           {state.counts.model_dump()}")
        print(f"  initialized_at:   {state.initialized_at}")
        if not args.write:
            print("\n(dry-run — use --write to persist)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(main())
