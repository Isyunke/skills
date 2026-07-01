"""Evidence Validator — enforces the three non-negotiable principles.

Replaces the ``hooks/truth-verification.sh`` and ``hooks/evidence-chain.sh``
scripts with a cross-platform, cross-agent Python validator that actually
blocks (not just warns) when the principles are violated.

Principles (see ``shared-references/core-principles.md``):
    1. truth_first      — every claim is backed by real, referenceable evidence
    2. evidence_chain   — every skill claim maps to project(s) + quantified result
    3. targeted_for_jd  — every resume is bound to a specific JD

Design notes
------------
* Pure function. Given a project root, returns a ``ValidationResult``. No
  side effects — call sites decide whether to persist ``_computed`` fields.
* Uses only the KB shape defined in ``tools.schemas`` — the validator
  itself is agnostic to how the KB got created (dialog / import / code
  trace / migration all produce the same shape).
* Every violation carries a ``fix`` suggestion; error messages follow the
  "what / why / how" template from docs/v2/07-ux-improvements.md §4.

CLI usage
---------
    python -m tools.evidence_validator [--project-root PATH] [--principle P]
                                       [--json] [--no-strict]

Exit codes:
    0 = all passed (may still have warnings)
    1 = one or more errors (principle violation)
    2 = warnings only (with --strict-warnings)
    3 = KB corrupted (schema parse failure)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Tuple, Union

from pydantic import ValidationError

from .io_utils import load_yaml
from .schemas import (
    EvidenceStrength,
    JobDescription,
    ProficiencyLevel,
    Project,
    Resume,
    SchemaVersionError,
    SkillTree,
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class Principle(str, Enum):
    TRUTH_FIRST = "truth_first"
    EVIDENCE_CHAIN = "evidence_chain"
    TARGETED_FOR_JD = "targeted_for_jd"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Violation:
    principle: Principle
    severity: Severity
    location: str                # e.g. "profile/skills/data.yaml#categories[0].skills[1]"
    message_zh: str
    message_en: str
    fix: str                     # actionable suggestion

    def to_dict(self) -> dict:
        return {
            "principle": self.principle.value,
            "severity": self.severity.value,
            "location": self.location,
            "message_zh": self.message_zh,
            "message_en": self.message_en,
            "fix": self.fix,
        }


@dataclass
class ValidationResult:
    passed: bool                        # True iff no ERROR-level violations
    violations: List[Violation] = field(default_factory=list)
    checked_files: int = 0
    principle_summary: Dict[str, str] = field(default_factory=dict)
    # e.g. {"truth_first": "pass", "evidence_chain": "fail", "targeted_for_jd": "warn"}

    def errors(self) -> List[Violation]:
        return [v for v in self.violations if v.severity == Severity.ERROR]

    def warnings(self) -> List[Violation]:
        return [v for v in self.violations if v.severity == Severity.WARNING]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checked_files": self.checked_files,
            "principle_summary": self.principle_summary,
            "violations": [v.to_dict() for v in self.violations],
            "errors_count": len(self.errors()),
            "warnings_count": len(self.warnings()),
        }


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------


@dataclass
class _LoadedKB:
    """Loaded pieces of the KB relevant to validation.

    Missing pieces are None — the validator degrades gracefully (a project
    without a skill tree is still checkable for internal STAR/quantification
    consistency).
    """

    project_root: Path
    skill_tree: Optional[SkillTree] = None
    projects: List[Project] = field(default_factory=list)
    project_paths: Dict[str, Path] = field(default_factory=dict)
    resumes: List[Tuple[Path, Resume]] = field(default_factory=list)
    jds: Dict[str, JobDescription] = field(default_factory=dict)
    load_errors: List[Violation] = field(default_factory=list)


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _wrap_pydantic_error(
    exc: ValidationError,
    principle: Principle,
    location: str,
) -> Violation:
    first = exc.errors()[0]
    field_path = ".".join(str(x) for x in first["loc"])
    msg = first["msg"]
    return Violation(
        principle=principle,
        severity=Severity.ERROR,
        location=f"{location}#{field_path}" if field_path else location,
        message_zh=f"数据结构错误：{msg}",
        message_en=f"Schema error: {msg}",
        fix=(
            f"修正 {location} 中字段 {field_path!r} 的值；"
            f"或跑 `resume migrate` 若这是 v1 数据。"
        ),
    )


def _load_kb(project_root: Path) -> _LoadedKB:
    kb = _LoadedKB(project_root=project_root)

    # --- skills tree
    skills_yaml = project_root / "profile" / "skills" / "data.yaml"
    if skills_yaml.is_file():
        try:
            kb.skill_tree = SkillTree.model_validate(load_yaml(skills_yaml))
        except ValidationError as e:
            kb.load_errors.append(_wrap_pydantic_error(e, Principle.EVIDENCE_CHAIN, _rel(skills_yaml, project_root)))
        except SchemaVersionError as e:
            kb.load_errors.append(_schema_version_violation(e, _rel(skills_yaml, project_root)))

    # --- projects
    projects_dir = project_root / "profile" / "projects"
    if projects_dir.is_dir():
        for sub in sorted(projects_dir.iterdir()):
            if not sub.is_dir():
                continue
            data_yaml = sub / "data.yaml"
            if not data_yaml.is_file():
                continue
            try:
                proj = Project.model_validate(load_yaml(data_yaml))
                kb.projects.append(proj)
                kb.project_paths[proj.id] = data_yaml
            except ValidationError as e:
                kb.load_errors.append(_wrap_pydantic_error(e, Principle.TRUTH_FIRST, _rel(data_yaml, project_root)))
            except SchemaVersionError as e:
                kb.load_errors.append(_schema_version_violation(e, _rel(data_yaml, project_root)))

    # --- resumes & jds
    resumes_dir = project_root / "resumes"
    if resumes_dir.is_dir():
        for jd_dir in sorted(resumes_dir.iterdir()):
            if not jd_dir.is_dir():
                continue
            # jd.yaml
            jd_yaml = jd_dir / "jd.yaml"
            if jd_yaml.is_file():
                try:
                    jd = JobDescription.model_validate(load_yaml(jd_yaml))
                    kb.jds[jd.id] = jd
                except ValidationError as e:
                    kb.load_errors.append(_wrap_pydantic_error(e, Principle.TARGETED_FOR_JD, _rel(jd_yaml, project_root)))
                except SchemaVersionError as e:
                    kb.load_errors.append(_schema_version_violation(e, _rel(jd_yaml, project_root)))
            # any resume-v*.yaml
            for resume_yaml in sorted(jd_dir.glob("resume-v*.yaml")):
                try:
                    resume = Resume.model_validate(load_yaml(resume_yaml))
                    kb.resumes.append((resume_yaml, resume))
                except ValidationError as e:
                    kb.load_errors.append(_wrap_pydantic_error(e, Principle.TARGETED_FOR_JD, _rel(resume_yaml, project_root)))
                except SchemaVersionError as e:
                    kb.load_errors.append(_schema_version_violation(e, _rel(resume_yaml, project_root)))

    return kb


def _schema_version_violation(exc: SchemaVersionError, location: str) -> Violation:
    return Violation(
        principle=Principle.TRUTH_FIRST,
        severity=Severity.ERROR,
        location=location,
        message_zh=f"schema 版本不匹配：文件是 {exc.found}，当前工具期望 {exc.expected}",
        message_en=f"Schema version mismatch: file={exc.found}, tool={exc.expected}",
        fix="跑 `resume migrate` 升级到当前 schema 版本。",
    )


# ---------------------------------------------------------------------------
# Principle checks
# ---------------------------------------------------------------------------


_PROFICIENCY_EVIDENCE_RULES: Dict[ProficiencyLevel, Dict[str, int]] = {
    ProficiencyLevel.KNOWN: {"min_projects": 0, "min_quantified": 0},
    ProficiencyLevel.PROFICIENT: {"min_projects": 1, "min_quantified": 0},
    ProficiencyLevel.EXPERT: {"min_projects": 2, "min_quantified": 1},
}


def _check_truth_first(kb: _LoadedKB) -> List[Violation]:
    """Every project's achievements must have a ``source``; every resume
    ``source_project`` reference must resolve to a real project.
    """
    v: List[Violation] = []
    project_ids = {p.id for p in kb.projects}

    # Projects: achievements must have non-empty source (already enforced by
    # Pydantic min_length=1). We additionally forbid "estimate" / "estimated"
    # as a source — the whole point is verifiable evidence.
    for p in kb.projects:
        proj_loc = _rel(kb.project_paths[p.id], kb.project_root)
        for i, a in enumerate(p.achievements):
            src = a.source.strip().lower()
            if src in {"estimate", "estimated", "guess", "assumed", "估算", "猜的"}:
                v.append(Violation(
                    principle=Principle.TRUTH_FIRST,
                    severity=Severity.ERROR,
                    location=f"{proj_loc}#achievements[{i}].source",
                    message_zh=f"achievement {a.metric!r} 的 source 是 {a.source!r}，不算真实证据。",
                    message_en=f"Achievement {a.metric!r} has non-evidence source {a.source!r}.",
                    fix=(
                        "把 source 改为可追溯的凭据（监控截图路径、BI 报表、commit 链接等），"
                        "或降级 achievement 为定性描述而不是数字。"
                    ),
                ))

    # Resumes: source_project references must resolve
    for resume_path, resume in kb.resumes:
        rloc = _rel(resume_path, kb.project_root)
        for ref in resume.project_refs():
            if ref not in project_ids:
                v.append(Violation(
                    principle=Principle.TRUTH_FIRST,
                    severity=Severity.ERROR,
                    location=f"{rloc} references {ref}",
                    message_zh=f"简历引用的项目 {ref!r} 在 profile/projects/ 中不存在。",
                    message_en=f"Resume references project {ref!r} which does not exist.",
                    fix=(
                        f"a) 跑 `resume intake dialog` 补充该项目；"
                        f"b) 或在简历中移除该引用；"
                        f"c) 或修正 id 拼写（现有: {sorted(project_ids)[:5]}...）。"
                    ),
                ))

    return v


def _check_evidence_chain(kb: _LoadedKB) -> List[Violation]:
    """Every skill claim's proficiency must be backed by enough projects
    and (for expert) quantified achievements.

    This also *derives* ``evidence_strength`` in memory but does not persist
    it — callers (e.g. state_builder or intake pipeline) do that.
    """
    v: List[Violation] = []
    if kb.skill_tree is None:
        return v

    project_by_id = {p.id: p for p in kb.projects}
    skills_loc = "profile/skills/data.yaml"

    for cat in kb.skill_tree.categories:
        for i, sk in enumerate(cat.skills):
            loc = f"{skills_loc}#categories[{cat.id}].skills[{sk.name}]"
            rules = _PROFICIENCY_EVIDENCE_RULES[sk.proficiency]
            refs = sk.evidence.projects

            # 1) referenced projects must exist
            unknown = [r for r in refs if r not in project_by_id]
            if unknown:
                v.append(Violation(
                    principle=Principle.EVIDENCE_CHAIN,
                    severity=Severity.ERROR,
                    location=loc,
                    message_zh=f"技能 {sk.name!r} 引用了不存在的项目：{unknown}",
                    message_en=f"Skill {sk.name!r} references unknown projects: {unknown}",
                    fix=(
                        "a) 补充这些项目：`resume intake dialog`；"
                        "b) 或从证据列表中移除；"
                        "c) 检查项目 id 拼写。"
                    ),
                ))

            # 2) proficiency requires N projects
            valid_refs = [r for r in refs if r in project_by_id]
            if len(valid_refs) < rules["min_projects"]:
                v.append(Violation(
                    principle=Principle.EVIDENCE_CHAIN,
                    severity=Severity.ERROR,
                    location=loc,
                    message_zh=(
                        f"技能 {sk.name!r} 声明 proficiency={sk.proficiency.value}，"
                        f"但仅有 {len(valid_refs)} 个项目支撑（需要 ≥{rules['min_projects']}）。"
                    ),
                    message_en=(
                        f"Skill {sk.name!r} claims {sk.proficiency.value} "
                        f"with only {len(valid_refs)} supporting projects "
                        f"(need ≥{rules['min_projects']})."
                    ),
                    fix=(
                        f"a) 补 {rules['min_projects'] - len(valid_refs)} 个项目做证据；"
                        f"b) 或降级 proficiency 到符合现有证据的等级。"
                    ),
                ))
                continue  # further quantified check moot

            # 3) expert requires ≥1 quantified achievement across refs
            if rules["min_quantified"] > 0:
                q_count = sum(
                    1
                    for pid in valid_refs
                    for ach in project_by_id[pid].achievements
                    if ach.is_quantified
                )
                if q_count < rules["min_quantified"]:
                    v.append(Violation(
                        principle=Principle.EVIDENCE_CHAIN,
                        severity=Severity.ERROR,
                        location=loc,
                        message_zh=(
                            f"技能 {sk.name!r} 声明 expert，但引用项目中没有一个含量化成果。"
                        ),
                        message_en=(
                            f"Skill {sk.name!r} claims expert but referenced projects "
                            "contain no quantified achievement."
                        ),
                        fix=(
                            "a) 补充 achievement 的量化数据 (before/after/delta 含数字)；"
                            "b) 或降级 proficiency 到 proficient。"
                        ),
                    ))

    return v


def _check_targeted_for_jd(kb: _LoadedKB) -> List[Violation]:
    """Every resume must point at a JD that actually exists in the same repo."""
    v: List[Violation] = []
    for resume_path, resume in kb.resumes:
        rloc = _rel(resume_path, kb.project_root)
        if resume.jd_id not in kb.jds:
            v.append(Violation(
                principle=Principle.TARGETED_FOR_JD,
                severity=Severity.ERROR,
                location=f"{rloc}#jd_id",
                message_zh=f"简历指向 jd_id={resume.jd_id!r}，但对应 jd.yaml 不存在。",
                message_en=f"Resume points to jd_id={resume.jd_id!r} but no matching jd.yaml exists.",
                fix=(
                    "a) 跑 `resume match` 分析该 JD；"
                    "b) 或修正 jd_id 让它匹配现有 JD 目录。"
                ),
            ))

    # Detect reuse: same resume-v file cross-referenced by two JDs by mistake.
    # (currently impossible given path scheme, but keep a placeholder)
    return v


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_project(
    project_root: Union[Path, str],
    principles: Optional[Iterable[Principle]] = None,
) -> ValidationResult:
    """Run all requested principle checks. Default: all three."""
    root = Path(project_root)
    kb = _load_kb(root)
    principles = list(principles) if principles else list(Principle)

    all_violations: List[Violation] = list(kb.load_errors)  # noqa: E501
    if Principle.TRUTH_FIRST in principles:
        all_violations.extend(_check_truth_first(kb))
    if Principle.EVIDENCE_CHAIN in principles:
        all_violations.extend(_check_evidence_chain(kb))
    if Principle.TARGETED_FOR_JD in principles:
        all_violations.extend(_check_targeted_for_jd(kb))

    # Per-principle summary
    summary: Dict[str, str] = {}
    for p in principles:
        matching = [v for v in all_violations if v.principle == p]
        if not matching:
            summary[p.value] = "pass"
        elif all(v.severity == Severity.WARNING for v in matching):
            summary[p.value] = "warn"
        else:
            summary[p.value] = "fail"

    has_error = any(v.severity == Severity.ERROR for v in all_violations)

    checked = (
        (1 if kb.skill_tree else 0)
        + len(kb.projects)
        + len(kb.resumes)
        + len(kb.jds)
    )

    return ValidationResult(
        passed=not has_error,
        violations=all_violations,
        checked_files=checked,
        principle_summary=summary,
    )


def compute_evidence_strength(
    skill_proficiency: ProficiencyLevel,
    referenced_projects: List[Project],
) -> EvidenceStrength:
    """Deterministically derive ``evidence_strength`` for a single skill.

    Used both by the validator (informational) and by intake pipelines that
    need to write the field before persisting.
    """
    if not referenced_projects:
        return EvidenceStrength.NONE
    quantified = sum(
        1 for p in referenced_projects if any(a.is_quantified for a in p.achievements)
    )
    if skill_proficiency == ProficiencyLevel.EXPERT:
        return EvidenceStrength.STRONG if (
            len(referenced_projects) >= 2 and quantified >= 1
        ) else EvidenceStrength.WEAK
    if skill_proficiency == ProficiencyLevel.PROFICIENT:
        return EvidenceStrength.STRONG if len(referenced_projects) >= 1 and quantified >= 1 else (
            EvidenceStrength.WEAK if referenced_projects else EvidenceStrength.NONE
        )
    # KNOWN
    return EvidenceStrength.WEAK if referenced_projects else EvidenceStrength.NONE


# ---------------------------------------------------------------------------
# Friendly text renderer
# ---------------------------------------------------------------------------


def render_result_text(result: ValidationResult, *, locale: str = "zh-CN") -> str:
    """Human-friendly report following the What/Why/How template."""
    zh = locale.startswith("zh")
    lines: List[str] = []
    lines.append("📋 Resume Alchemist · Evidence Validation Report")
    lines.append(f"   checked files: {result.checked_files}")
    lines.append("")
    for principle, status in result.principle_summary.items():
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}[status]
        lines.append(f"   {icon} {principle}: {status}")
    lines.append("")
    if not result.violations:
        lines.append("🎉 全部通过。" if zh else "🎉 All principles satisfied.")
        return "\n".join(lines)

    lines.append("─" * 60)
    for v in result.violations:
        head = "❌" if v.severity == Severity.ERROR else "⚠️"
        msg = v.message_zh if zh else v.message_en
        lines.append(f"{head} [{v.principle.value}] {v.location}")
        lines.append(f"   what:  {msg}")
        lines.append(f"   how:   {v.fix}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="resume-validate",
        description="Validate a resume-alchemist project against the 3 principles.",
    )
    p.add_argument(
        "--project-root",
        default=".",
        help="Path to the resume project (defaults to CWD).",
    )
    p.add_argument(
        "--principle",
        choices=[p.value for p in Principle],
        action="append",
        help="Restrict to specific principle(s). May be passed multiple times.",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON instead of prose.")
    p.add_argument(
        "--no-strict",
        action="store_true",
        help="Do not exit non-zero on ERROR violations (still exits 3 on KB corruption).",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _cli_argparser().parse_args(argv)
    root = Path(args.project_root).resolve()
    principles = (
        [Principle(p) for p in args.principle] if args.principle else None
    )
    try:
        result = validate_project(root, principles=principles)
    except Exception as e:  # pragma: no cover — defensive
        print(f"❌ validator crashed: {e}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_result_text(result))

    if args.no_strict:
        return 0
    if result.errors():
        return 1
    if result.warnings():
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
