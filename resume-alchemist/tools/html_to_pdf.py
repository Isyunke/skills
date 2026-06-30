#!/usr/bin/env python3
"""
HTML to PDF converter for resume-alchemist.

Usage:
    python html_to_pdf.py <html_path> <pdf_path>
    python html_to_pdf.py --check          # Check available PDF engines

Requirements:
    - weasyprint (preferred on Linux/Mac, needs GTK on Windows)
    - playwright (preferred on Windows, no system dependencies)
"""

import sys
import os
from pathlib import Path


def check_engines():
    """Check which PDF engines are available."""
    results = {}

    # Check weasyprint
    try:
        import weasyprint
        # Try to actually load the library (may fail on Windows without GTK)
        weasyprint.HTML(string="<h1>test</h1>").write_pdf("/dev/null") if sys.platform != 'win32' else None
        results['weasyprint'] = True
    except ImportError:
        results['weasyprint'] = False
    except Exception:
        results['weasyprint'] = False  # Installed but broken (e.g., missing GTK)

    # Check playwright
    try:
        from playwright.sync_api import sync_playwright
        results['playwright'] = True
    except ImportError:
        results['playwright'] = False

    return results


def html_to_pdf_weasyprint(html_path: str, pdf_path: str) -> bool:
    """Convert HTML to PDF using weasyprint."""
    try:
        import weasyprint
        html = Path(html_path).read_text(encoding='utf-8')
        weasyprint.HTML(string=html).write_pdf(pdf_path)
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"  weasyprint error: {e}")
        return False


def html_to_pdf_playwright(html_path: str, pdf_path: str) -> bool:
    """Convert HTML to PDF using playwright."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.pdf(path=pdf_path)
            browser.close()
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"  playwright error: {e}")
        return False


def main():
    # Ensure UTF-8 output on Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Handle --check flag
    if len(sys.argv) >= 2 and sys.argv[1] == '--check':
        engines = check_engines()
        print("PDF Engine Status:")
        for engine, available in engines.items():
            status = "available" if available else "not available"
            print(f"  {engine}: {status}")
        return

    if len(sys.argv) < 3:
        print("Usage: python html_to_pdf.py <html_path> <pdf_path>")
        print("       python html_to_pdf.py --check")
        sys.exit(1)

    html_path = sys.argv[1]
    pdf_path = sys.argv[2]

    # Validate input
    if not os.path.exists(html_path):
        print(f"HTML file not found: {html_path}")
        sys.exit(1)

    # Create output directory if needed
    pdf_dir = os.path.dirname(pdf_path)
    if pdf_dir and not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)

    # On Windows, try playwright first (weasyprint needs GTK)
    # On Linux/Mac, try weasyprint first
    if sys.platform == 'win32':
        engines = [('playwright', html_to_pdf_playwright), ('weasyprint', html_to_pdf_weasyprint)]
    else:
        engines = [('weasyprint', html_to_pdf_weasyprint), ('playwright', html_to_pdf_playwright)]

    for engine_name, engine_func in engines:
        if engine_func(html_path, pdf_path):
            print(f"PDF generated using {engine_name}: {pdf_path}")
            return

    # No engine available
    print("No PDF engine available.")
    print("Please install one of:")
    print("  - playwright: pip install playwright && playwright install chromium")
    print("  - weasyprint: pip install weasyprint (requires GTK on Windows)")
    sys.exit(1)


if __name__ == "__main__":
    main()
