"""CLI-level tests for the v2 tools.

These invoke the `main()` entrypoints directly (in-process) rather than
spawning subprocesses, so coverage is captured cleanly.
"""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from tools import evidence_validator, state_builder, keyword_matcher, html_to_pdf, io_utils


# ---------------------------------------------------------------------------
# evidence_validator CLI
# ---------------------------------------------------------------------------


class TestEvidenceValidatorCLI:
    def test_cli_empty_repo_exits_zero(self, tmp_path: Path, capsys):
        code = evidence_validator.main(["--project-root", str(tmp_path)])
        out = capsys.readouterr().out
        assert code == 0
        assert "Evidence Validation Report" in out

    def test_cli_json_output(self, tmp_path: Path, capsys):
        code = evidence_validator.main(["--project-root", str(tmp_path), "--json"])
        out = capsys.readouterr().out
        assert code == 0
        payload = json.loads(out)
        assert payload["passed"] is True
        assert "principle_summary" in payload

    def test_cli_no_strict_swallows_errors(self, tmp_path: Path, capsys):
        # Force an evidence_chain violation.
        io_utils.dump_yaml(tmp_path / "profile" / "skills" / "data.yaml", {
            "schema_version": "2.0",
            "schema_type": "skill_tree",
            "categories": [{
                "schema_version": "2.0",
                "id": "p",
                "label": {"zh": "p"},
                "skills": [{
                    "schema_version": "2.0",
                    "name": "Python",
                    "proficiency": "expert",
                    "evidence_strength": "none",
                    "evidence": {"schema_version": "2.0", "projects": []},
                }],
            }],
        })
        # Strict → exit 1
        code_strict = evidence_validator.main(["--project-root", str(tmp_path)])
        assert code_strict == 1
        capsys.readouterr()
        # No-strict → exit 0
        code_lax = evidence_validator.main(
            ["--project-root", str(tmp_path), "--no-strict"]
        )
        assert code_lax == 0

    def test_cli_filter_by_principle(self, tmp_path: Path, capsys):
        # evidence_chain violation exists, but we filter to truth_first only
        io_utils.dump_yaml(tmp_path / "profile" / "skills" / "data.yaml", {
            "schema_version": "2.0",
            "schema_type": "skill_tree",
            "categories": [{
                "schema_version": "2.0",
                "id": "p",
                "label": {"zh": "p"},
                "skills": [{
                    "schema_version": "2.0",
                    "name": "Python",
                    "proficiency": "expert",
                    "evidence_strength": "none",
                    "evidence": {"schema_version": "2.0", "projects": []},
                }],
            }],
        })
        code = evidence_validator.main([
            "--project-root", str(tmp_path),
            "--principle", "truth_first",
        ])
        assert code == 0  # evidence_chain violation is filtered out


# ---------------------------------------------------------------------------
# state_builder CLI
# ---------------------------------------------------------------------------


class TestStateBuilderCLI:
    def test_cli_dry_run_prints_summary(self, tmp_path: Path, capsys):
        code = state_builder.main(["--project-root", str(tmp_path)])
        out = capsys.readouterr().out
        assert code == 0
        assert "Rebuilt state" in out
        assert "dry-run" in out
        # state file should NOT exist (dry-run)
        assert not (tmp_path / state_builder.STATE_FILENAME).is_file()

    def test_cli_write_persists_file(self, tmp_path: Path, capsys):
        code = state_builder.main(["--project-root", str(tmp_path), "--write"])
        assert code == 0
        state_path = tmp_path / state_builder.STATE_FILENAME
        assert state_path.is_file()
        raw = io_utils.load_json(state_path)
        assert raw["schema_type"] == "state"

    def test_cli_json_output(self, tmp_path: Path, capsys):
        code = state_builder.main(["--project-root", str(tmp_path), "--json"])
        out = capsys.readouterr().out
        assert code == 0
        payload = json.loads(out)
        assert payload["schema_version"] == "2.0"


# ---------------------------------------------------------------------------
# keyword_matcher CLI + pack loading
# ---------------------------------------------------------------------------


class TestKeywordMatcherCLI:
    def test_list_industries(self, capsys):
        code = keyword_matcher.main(["--list-industries"])
        out = capsys.readouterr().out
        assert code == 0
        # tech / product / design packs shipped in P0
        for expected in ("tech", "product", "design"):
            assert expected in out

    def test_match_end_to_end_text_output(self, tmp_path: Path, capsys):
        jd = tmp_path / "jd.md"
        jd.write_text("Python expert, Kubernetes, PostgreSQL", encoding="utf-8")
        resume = tmp_path / "resume.md"
        resume.write_text("Python, PostgreSQL, Redis", encoding="utf-8")
        code = keyword_matcher.main([str(resume), str(jd)])
        assert code == 0
        out = capsys.readouterr().out
        assert "Python" in out and "PostgreSQL" in out
        assert "Kubernetes" in out  # missing keyword

    def test_match_json_output(self, tmp_path: Path, capsys):
        jd = tmp_path / "jd.md"
        jd.write_text("Python, K8s", encoding="utf-8")
        resume = tmp_path / "resume.md"
        resume.write_text("Python", encoding="utf-8")
        code = keyword_matcher.main([str(resume), str(jd), "--json"])
        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert "matched" in payload
        assert "weighted_coverage" in payload
        assert 0.0 <= payload["weighted_coverage"] <= 1.0

    def test_industry_flag_switches_pack(self, tmp_path: Path, capsys):
        jd = tmp_path / "jd.md"
        # A/B testing is a product-pack keyword; tech pack does not include it.
        jd.write_text("需要 A/B Testing 经验", encoding="utf-8")
        resume = tmp_path / "resume.md"
        resume.write_text("做过 A/B testing 项目", encoding="utf-8")
        code = keyword_matcher.main([
            str(resume), str(jd), "--industry", "product", "--json"
        ])
        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert "A/B Testing" in payload["matched"]

    def test_usage_when_missing_args(self, capsys):
        code = keyword_matcher.main([])
        assert code == 1
        assert "Usage" in capsys.readouterr().out


class TestKeywordPack:
    def test_load_tech_pack(self):
        pack = keyword_matcher.load_pack("tech")
        assert pack.industry == "tech"
        assert any(e.canonical == "Kubernetes" for e in pack.entries)
        entry = pack.find("K8s")
        assert entry is not None and entry.canonical == "Kubernetes"

    def test_missing_pack_raises(self):
        with pytest.raises(FileNotFoundError):
            keyword_matcher.load_pack("does-not-exist")

    def test_merge_dedups_on_canonical(self):
        p1 = keyword_matcher.KeywordPack(industry="a", entries=[
            keyword_matcher.KeywordEntry(canonical="X", weight=1.0),
        ])
        p2 = keyword_matcher.KeywordPack(industry="b", entries=[
            keyword_matcher.KeywordEntry(canonical="X", weight=0.5),
            keyword_matcher.KeywordEntry(canonical="Y", weight=1.0),
        ])
        merged = p1.merge(p2)
        by_name = {e.canonical: e for e in merged.entries}
        assert by_name["X"].weight == 0.5  # p2 wins on collision
        assert "Y" in by_name

    def test_weighted_coverage_reflects_weights(self):
        pack = keyword_matcher.load_pack("tech")
        # Kubernetes weight=1.0, GraphQL weight=0.7 in tech pack.
        # If JD wants both but resume has only Kubernetes, weighted > raw.
        result = keyword_matcher.match_keywords(
            jd_keywords={"Kubernetes", "GraphQL"},
            resume_keywords={"Kubernetes"},
            pack=pack,
        )
        assert result["coverage"] == pytest.approx(0.5)
        assert result["weighted_coverage"] > 0.5  # Kubernetes carries more weight


# ---------------------------------------------------------------------------
# html_to_pdf CLI (env-independent branches only)
# ---------------------------------------------------------------------------


class TestHtmlToPdfCLI:
    def test_check_no_engines(self, capsys):
        # In CI without weasyprint/playwright installed, --check should exit 2.
        code = html_to_pdf.main(["--check"])
        out = capsys.readouterr().out
        assert "PDF engine environment check" in out
        # Exit code depends on whether engines are installed; accept 0 or 2
        assert code in (0, 2)

    def test_usage_when_no_args(self, capsys):
        code = html_to_pdf.main([])
        assert code == 1
        err = capsys.readouterr().err
        assert "Usage" in err

    def test_unknown_engine_raises(self, tmp_path: Path):
        html = tmp_path / "in.html"
        html.write_text("<h1>hi</h1>", encoding="utf-8")
        with pytest.raises(ValueError):
            html_to_pdf.html_to_pdf(str(html), str(tmp_path / "out.pdf"), engine="lolzip")

    def test_missing_input_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            html_to_pdf.html_to_pdf(
                str(tmp_path / "nope.html"), str(tmp_path / "out.pdf")
            )

    def test_no_engine_available_returns_2(self, tmp_path: Path, monkeypatch, capsys):
        # Force both engine functions to return False, simulating "installed but broken"
        monkeypatch.setattr(html_to_pdf, "ENGINES", {
            "weasyprint": lambda *_a, **_k: False,
            "playwright": lambda *_a, **_k: False,
        })
        html = tmp_path / "in.html"
        html.write_text("<h1>hi</h1>", encoding="utf-8")
        code = html_to_pdf.main([str(html), str(tmp_path / "out.pdf")])
        assert code == 2
