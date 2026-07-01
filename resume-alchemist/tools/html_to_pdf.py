#!/usr/bin/env python3
"""
HTML to PDF converter for resume-alchemist.

v2 upgrades over v1:
    * ``--check`` gives a full environment report with actionable install
      hints, per-engine health status, and a recommendation.
    * ``--engine {auto,weasyprint,playwright}`` lets the caller pin one.
    * Engine selection uses a shared preference order defined by
      ``ENGINE_ORDER`` — Windows prefers playwright, POSIX prefers
      weasyprint, but ``--engine`` overrides.
    * Atomic write is delegated to ``tools.io_utils`` so v2 has a single
      canonical implementation. A thin ``atomic_write`` shim is re-exported
      here so pre-existing tests keep working.
    * All exit codes are documented: 0 success, 1 usage, 2 no engine
      available, 3 engine crashed on this file.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# Re-export atomic_write from io_utils so existing tests importing
# ``tools.html_to_pdf.atomic_write`` still work.
try:
    from .io_utils import atomic_write_bytes as atomic_write  # noqa: F401
except ImportError:  # pragma: no cover — fallback for standalone execution
    import tempfile

    def atomic_write(path, data):  # type: ignore[no-redef]
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(data if isinstance(data, (bytes, bytearray)) else data.encode())
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, target)


EngineFn = Callable[[str, str], bool]


# ---------------------------------------------------------------------------
# Engine implementations
# ---------------------------------------------------------------------------


def html_to_pdf_weasyprint(html_path: str, pdf_path: str) -> bool:
    """Convert HTML to PDF using WeasyPrint.

    Returns True on success, False if the engine isn't importable or if
    conversion raised (with the error printed to stderr).
    """
    try:
        import weasyprint  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        html = Path(html_path).read_text(encoding="utf-8")
        weasyprint.HTML(string=html, base_url=os.path.dirname(os.path.abspath(html_path))).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"  weasyprint error: {e}", file=sys.stderr)
        return False


def html_to_pdf_playwright(html_path: str, pdf_path: str) -> bool:
    """Convert HTML to PDF using Playwright's headless Chromium."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"file://{os.path.abspath(html_path)}")
                page.pdf(path=pdf_path, format="A4", print_background=True)
            finally:
                browser.close()
        return True
    except Exception as e:
        print(f"  playwright error: {e}", file=sys.stderr)
        return False


ENGINES: Dict[str, EngineFn] = {
    "weasyprint": html_to_pdf_weasyprint,
    "playwright": html_to_pdf_playwright,
}


def _default_engine_order() -> List[str]:
    """Return preferred engine order for the current platform."""
    if sys.platform == "win32":
        # Playwright avoids the notorious GTK requirement on Windows.
        return ["playwright", "weasyprint"]
    return ["weasyprint", "playwright"]


# ---------------------------------------------------------------------------
# Environment check
# ---------------------------------------------------------------------------


def _probe_weasyprint() -> Tuple[bool, str]:
    try:
        import weasyprint  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False, "not installed. Install with: pip install weasyprint (needs GTK/libpangoft2 on Windows)"
    # Deeper probe: try to actually render something small on non-Windows.
    if sys.platform != "win32":
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                out = os.path.join(td, "probe.pdf")
                weasyprint.HTML(string="<h1>probe</h1>").write_pdf(out)
        except Exception as e:  # pragma: no cover — env-specific
            return False, f"installed but failed at runtime: {e}"
    return True, "ready"


def _probe_playwright() -> Tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        return False, "not installed. Install with: pip install playwright && python -m playwright install chromium"
    # Deeper probe: try to launch chromium briefly.
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
    except Exception as e:
        msg = str(e).splitlines()[0]
        return False, f"installed but chromium not ready ({msg}). Try: python -m playwright install chromium"
    return True, "ready"


def check_engines() -> Dict[str, bool]:
    """Return legacy-shaped dict for backward compatibility with v1 callers."""
    ok_w, _ = _probe_weasyprint()
    ok_p, _ = _probe_playwright()
    return {"weasyprint": ok_w, "playwright": ok_p}


def check_engines_detailed() -> Dict[str, Dict]:
    """Return per-engine detailed status.

    ``{"engine": {"available": bool, "detail": str}}``
    """
    ok_w, msg_w = _probe_weasyprint()
    ok_p, msg_p = _probe_playwright()
    return {
        "weasyprint": {"available": ok_w, "detail": msg_w},
        "playwright": {"available": ok_p, "detail": msg_p},
    }


def _print_check_report(details: Dict[str, Dict]) -> int:
    """Return an exit code (0 if any engine available, 2 otherwise)."""
    print("PDF engine environment check")
    print("=" * 40)
    for name in _default_engine_order():
        info = details[name]
        status = "OK" if info["available"] else "NOT AVAILABLE"
        print(f"  [{status:14}] {name}")
        print(f"                   {info['detail']}")
    any_ok = any(v["available"] for v in details.values())
    print()
    if any_ok:
        preferred = next(
            (name for name in _default_engine_order() if details[name]["available"]),
            None,
        )
        print(f"Recommendation: use --engine {preferred} (default on this platform)")
        return 0
    print("No PDF engine available. Install at least one of the above and re-run --check.")
    return 2


# ---------------------------------------------------------------------------
# Conversion API
# ---------------------------------------------------------------------------


def html_to_pdf(
    html_path: str,
    pdf_path: str,
    *,
    engine: str = "auto",
) -> Tuple[bool, str]:
    """Convert ``html_path`` to ``pdf_path``. Returns (success, engine_used).

    Ensures the output directory exists. Does not overwrite via atomic
    rename — callers wanting atomicity should render into a temp path and
    then use ``tools.io_utils.atomic_write_bytes``. PDFs are inherently
    large so we don't buffer them in memory here.
    """
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    pdf_dir = os.path.dirname(pdf_path)
    if pdf_dir and not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)

    if engine != "auto":
        if engine not in ENGINES:
            raise ValueError(
                f"unknown engine {engine!r}; supported: {sorted(ENGINES.keys())}"
            )
        order = [engine]
    else:
        order = _default_engine_order()

    for name in order:
        fn = ENGINES[name]
        if fn(html_path, pdf_path):
            return True, name

    return False, ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _ensure_utf8_stdio() -> None:
    if sys.platform != "win32":
        return
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


def _cli_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="html_to_pdf",
        description="Convert an HTML resume to PDF using WeasyPrint or Playwright.",
    )
    p.add_argument("html_path", nargs="?", help="Path to input HTML.")
    p.add_argument("pdf_path", nargs="?", help="Path to output PDF.")
    p.add_argument(
        "--engine",
        choices=["auto", "weasyprint", "playwright"],
        default="auto",
        help="Force a specific engine (default: auto by platform).",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Print a detailed engine environment report and exit.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    _ensure_utf8_stdio()
    args = _cli_argparser().parse_args(argv)

    if args.check:
        return _print_check_report(check_engines_detailed())

    if not args.html_path or not args.pdf_path:
        print(
            "Usage: python html_to_pdf.py <html_path> <pdf_path> [--engine auto|weasyprint|playwright]\n"
            "       python html_to_pdf.py --check",
            file=sys.stderr,
        )
        return 1

    try:
        ok, engine_used = html_to_pdf(args.html_path, args.pdf_path, engine=args.engine)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if ok:
        print(f"✅ PDF generated using {engine_used}: {args.pdf_path}")
        return 0

    print("❌ No PDF engine available or all engines failed.", file=sys.stderr)
    print(
        "Run `python -m tools.html_to_pdf --check` to see what's missing.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
