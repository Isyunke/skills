#!/usr/bin/env python3
"""
Keyword matcher for resume-alchemist.

v2 upgrades:
    * Keyword packs are loaded from YAML files in ``tools/data/keywords/``
      instead of being hardcoded, so users can extend them.
    * Aliases are supported (e.g. ``K8s`` <-> ``Kubernetes``).
    * Weights per keyword. Coverage is computed as a weighted score, not
      just a raw ratio.
    * ``load_pack(industry)`` returns a structured object usable from the
      v2 tools layer.
    * The legacy CLI (``python keyword_matcher.py <resume> <jd>``) is
      preserved for backward compatibility with existing tests/scripts.
"""
from __future__ import annotations

import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml


DATA_DIR = Path(__file__).resolve().parent / "data" / "keywords"


# ---------------------------------------------------------------------------
# Structured pack model
# ---------------------------------------------------------------------------


@dataclass
class KeywordEntry:
    canonical: str
    aliases: List[str] = field(default_factory=list)
    weight: float = 1.0
    category: str = ""

    def all_terms(self) -> List[str]:
        return [self.canonical, *self.aliases]


@dataclass
class KeywordPack:
    industry: str
    entries: List[KeywordEntry] = field(default_factory=list)

    def all_canonicals(self) -> List[str]:
        return [e.canonical for e in self.entries]

    def find(self, term: str) -> Optional[KeywordEntry]:
        needle = term.lower()
        for e in self.entries:
            for t in e.all_terms():
                if t.lower() == needle:
                    return e
        return None

    def merge(self, other: "KeywordPack") -> "KeywordPack":
        """Combine two packs, ``other`` overriding on canonical name collision."""
        by_canonical: Dict[str, KeywordEntry] = {
            e.canonical.lower(): e for e in self.entries
        }
        for e in other.entries:
            by_canonical[e.canonical.lower()] = e
        return KeywordPack(
            industry=f"{self.industry}+{other.industry}",
            entries=list(by_canonical.values()),
        )


def load_pack(industry: str = "tech") -> KeywordPack:
    """Load a keyword pack from ``tools/data/keywords/<industry>.yaml``.

    Raises FileNotFoundError if the pack is missing.
    """
    path = DATA_DIR / f"{industry}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"keyword pack not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries: List[KeywordEntry] = []
    for cat_id, items in (raw.get("categories") or {}).items():
        for item in items:
            entries.append(
                KeywordEntry(
                    canonical=str(item["canonical"]),
                    aliases=[str(a) for a in (item.get("aliases") or [])],
                    weight=float(item.get("weight", 1.0)),
                    category=str(cat_id),
                )
            )
    return KeywordPack(industry=str(raw.get("industry", industry)), entries=entries)


def available_industries() -> List[str]:
    if not DATA_DIR.is_dir():
        return []
    return sorted(p.stem for p in DATA_DIR.glob("*.yaml"))


# ---------------------------------------------------------------------------
# Extraction & matching
# ---------------------------------------------------------------------------


def _contains_term(text_lower: str, term: str) -> bool:
    """Case-insensitive whole-token match for English; substring for Chinese."""
    if any("\u4e00" <= c <= "\u9fff" for c in term):
        return term in text_lower  # Chinese: substring is fine
    # English: word-boundary match; treat '.', '+', '/', '-' as part of term
    pattern = r"(?<![A-Za-z0-9])" + re.escape(term.lower()) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text_lower) is not None


def extract_keywords(text: str, pack: Optional[KeywordPack] = None) -> Set[str]:
    """Return the set of canonical keywords from ``pack`` that appear in ``text``.

    Aliases are resolved back to their canonical form. ``pack`` defaults to
    the ``tech`` pack for backward compatibility with v1 callers.
    """
    if pack is None:
        pack = load_pack("tech")
    text_lower = text.lower()
    found: Set[str] = set()
    for entry in pack.entries:
        for term in entry.all_terms():
            if _contains_term(text_lower, term):
                found.add(entry.canonical)
                break
    return found


def match_keywords(
    jd_keywords: Set[str],
    resume_keywords: Set[str],
    pack: Optional[KeywordPack] = None,
) -> Dict:
    """Compare two keyword sets.

    Returns a dict with the same shape as v1, plus ``weighted_coverage``.
    """
    matched = jd_keywords & resume_keywords
    missing = jd_keywords - resume_keywords
    extra = resume_keywords - jd_keywords

    coverage = len(matched) / len(jd_keywords) if jd_keywords else 0.0

    weighted_coverage = coverage
    if pack is not None and jd_keywords:
        weights = {e.canonical: e.weight for e in pack.entries}
        matched_w = sum(weights.get(k, 1.0) for k in matched)
        total_w = sum(weights.get(k, 1.0) for k in jd_keywords)
        weighted_coverage = matched_w / total_w if total_w else 0.0

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "coverage": coverage,
        "weighted_coverage": weighted_coverage,
    }


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------

# v1 exposed a ``DOMAIN_KEYWORDS`` module attribute; some tests import it.
# Rebuild it lazily from the tech pack so old code keeps working.

def _build_legacy_domain_keywords() -> Dict[str, List[str]]:
    try:
        pack = load_pack("tech")
    except FileNotFoundError:
        return {}
    grouped: Dict[str, List[str]] = {}
    for e in pack.entries:
        grouped.setdefault(e.category or "misc", []).append(e.canonical)
    return grouped


DOMAIN_KEYWORDS = _build_legacy_domain_keywords()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _ensure_utf8_stdio() -> None:
    if sys.platform != "win32":
        return
    # Only wrap when the streams are real terminals. Under pytest capsys
    # (or any redirection to a StringIO) the buffer attribute is either
    # missing or wrapping it would bypass the test's capture layer.
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            continue
        if not getattr(stream, "isatty", lambda: False)():
            continue
        try:
            setattr(sys, name, io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))
        except (AttributeError, ValueError):
            pass


def _print_report(result: Dict, jd_keywords: Set[str], resume_keywords: Set[str]) -> None:
    print("Keyword Match Report")
    print("=" * 50)
    print(f"\nJD Keywords ({len(jd_keywords)}):")
    print(f"  {', '.join(sorted(jd_keywords))}")
    print(f"\nResume Keywords ({len(resume_keywords)}):")
    print(f"  {', '.join(sorted(resume_keywords))}")
    print(f"\nMatched ({len(result['matched'])}):")
    print(f"  {', '.join(sorted(result['matched']))}")
    print(f"\nMissing ({len(result['missing'])}):")
    print(f"  {', '.join(sorted(result['missing']))}")
    print(f"\nExtra ({len(result['extra'])}):")
    print(f"  {', '.join(sorted(result['extra']))}")
    print(f"\nCoverage:          {result['coverage']:.1%}")
    print(f"Weighted coverage: {result['weighted_coverage']:.1%}")


def main(argv: Optional[List[str]] = None) -> int:
    _ensure_utf8_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)

    industry = "tech"
    json_out = False
    positional: List[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--industry", "-i") and i + 1 < len(argv):
            industry = argv[i + 1]
            i += 2
            continue
        if a == "--json":
            json_out = True
            i += 1
            continue
        if a == "--list-industries":
            for name in available_industries():
                print(name)
            return 0
        positional.append(a)
        i += 1

    if len(positional) < 2:
        print(
            "Usage: python keyword_matcher.py <resume_path> <jd_path> "
            "[--industry tech] [--json]"
        )
        return 1

    resume_path, jd_path = positional[0], positional[1]
    pack = load_pack(industry)
    resume_text = Path(resume_path).read_text(encoding="utf-8")
    jd_text = Path(jd_path).read_text(encoding="utf-8")

    resume_kws = extract_keywords(resume_text, pack)
    jd_kws = extract_keywords(jd_text, pack)
    result = match_keywords(jd_kws, resume_kws, pack)

    if json_out:
        payload = {
            k: (sorted(list(v)) if isinstance(v, set) else v)
            for k, v in result.items()
        }
        payload["industry"] = industry
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_report(result, jd_kws, resume_kws)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
