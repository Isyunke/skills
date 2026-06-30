---
name: resume-export
description: 将 HTML 简历转换为 PDF。触发词："导出 PDF"/"生成 PDF"。
argument-hint: [jd-id]
allowed-tools: Read, Write, Bash
---

# /resume-export — 导出 PDF

将 HTML 简历转换为 PDF，用于简历投递。

## Overview

```
[用户：导出 PDF]
  ↓
[Phase 0: 读取 HTML 简历]
  ↓
[Phase 1: 转换为 PDF]
  ↓
[Phase 2: 输出结果]
```

## Constants

- **PDF_ENGINE = weasyprint** — 默认使用 weasyprint
- **FALLBACK_ENGINE = playwright** — 备选方案

## Inputs

| 必填 | 来源 |
|---|---|
| HTML 简历 | `resumes/jd-<NNN>-<short>/resume.html` |

## Workflow

### Phase 0: 读取 HTML 简历

1. 读取 `.resume-state.json` → 获取 `active_jd_id`
2. 读取 `resumes/jd-<NNN>-<short>/resume.html`
3. 验证 HTML 文件有效性

### Phase 1: 转换为 PDF

使用 Python 脚本转换：

```python
#!/usr/bin/env python3
"""
HTML to PDF converter for resume-alchemist.
"""

import sys
import os
from pathlib import Path

def html_to_pdf_weasyprint(html_path: str, pdf_path: str):
    """Convert HTML to PDF using weasyprint."""
    try:
        import weasyprint
        html = Path(html_path).read_text(encoding='utf-8')
        weasyprint.HTML(string=html).write_pdf(pdf_path)
        return True
    except ImportError:
        return False

def html_to_pdf_playwright(html_path: str, pdf_path: str):
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

def atomic_write(file_path: str, content: bytes):
    """Atomic write using .tmp -> rename."""
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(content)
    os.replace(tmp_path, file_path)

def main():
    if len(sys.argv) < 3:
        print("Usage: python html_to_pdf.py <html_path> <pdf_path>")
        sys.exit(1)

    html_path = sys.argv[1]
    pdf_path = sys.argv[2]

    # Try weasyprint first
    if html_to_pdf_weasyprint(html_path, pdf_path):
        print(f"✅ PDF generated using weasyprint: {pdf_path}")
        return

    # Fallback to playwright
    if html_to_pdf_playwright(html_path, pdf_path):
        print(f"✅ PDF generated using playwright: {pdf_path}")
        return

    print("❌ No PDF engine available. Install weasyprint or playwright.")
    sys.exit(1)

if __name__ == "__main__":
    main()
```

### Phase 2: 输出结果

```
✅ PDF 已生成：resumes/jd-001-xx公司后端/resume.pdf

📁 文件：
- resumes/jd-001-xx公司后端/resume.html
- resumes/jd-001-xx公司后端/resume.pdf

💡 下一步：
- 投递简历？→ 直接使用 PDF
- 准备面试？→ "准备面试"
- 优化简历？→ "优化一下简历"
```

## Key Rules

1. **原子写**——PDF 生成使用 .tmp → rename
2. **版本管理**——PDF 与 HTML 版本对应
3. **引擎选择**——优先 weasyprint，备选 playwright

## Refusals

- 「HTML 还没生成，先导出 PDF」 → 拒绝。先生成 HTML，再导出 PDF

## Integration

- 上游：`/resume-build` 生成 HTML 简历
- 输出：PDF 文件用于投递
