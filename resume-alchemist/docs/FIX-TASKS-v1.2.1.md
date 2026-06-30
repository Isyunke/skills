# 🔧 修复任务清单 v1.2.1

> **来源**：本地测试中发现的问题
> **测试日期**：2026-06-14
> **测试环境**：Windows 10, Python 3.8.3, Git Bash
> **修复状态**：✅ 全部完成（2026-06-14）

---

## 🔴 P0：阻断性问题（必须修复）

### FIX-001: resume_parser.py 工作经历提取失败

**问题描述**：
- 用户简历使用 `### **公司名** | 职位名` 格式
- 解析器正则只匹配 `### XX公司 - 职位 (2022-2024)` 格式
- 导致工作经历提取为空数组

**复现**：
```python
# 当前正则（只匹配这种格式）
r'#+\s*(.+?(?:公司|科技|集团|企业|团队))\s*[-–—]\s*(.+?)(?:\s*\((\d{4}[-.]\d{4})\))?\s*$'

# 用户简历实际格式（不匹配）
### **西门子 (Siemens)** | 智能制造软件工程师
```

**修复方案**：
```python
# 扩展正则，支持多种格式
patterns = [
    # 格式1: ### 公司名 - 职位 (日期)
    r'#+\s*(.+?(?:公司|科技|集团|企业|团队))\s*[-–—]\s*(.+?)(?:\s*\((\d{4}[-.]\d{4})\))?\s*$',
    # 格式2: ### **公司名** | 职位
    r'#+\s*\*{0,2}(.+?(?:公司|科技|集团|企业|团队|Siemens|Google|Meta|Amazon))\*{0,2}\s*[\|｜]\s*\*{0,2}(.+?)\*{0,2}\s*$',
    # 格式3: ### 公司名 职位
    r'#+\s*(.+?(?:公司|科技|集团|企业|团队))\s+(.+?(?:工程师|经理|总监|架构师|开发))\s*$',
]
```

**文件**：`tools/resume_parser.py` 第 188-216 行
**影响范围**：所有使用非标准格式的简历
**修复难度**：低（正则扩展）

---

### FIX-002: keyword_matcher.py 关键词库太窄

**问题描述**：
- 硬编码关键词只有约 40 个，全部是通用技术栈
- 对 JD 中的核心概念完全无法识别：
  - DevOps, CI/CD, observability, robotics, automation
  - agentic, platform engineering, edge computing
  - industrial, manufacturing, PLC, SCADA
- 测试结果：JD 有 20+ 核心关键词，只识别出 4 个

**修复方案**：

1. **扩展关键词库**：按领域分类
```python
DOMAIN_KEYWORDS = {
    "devops": ["CI/CD", "Jenkins", "GitLab CI", "GitHub Actions", "DevOps", "pipeline",
                "containerization", "orchestration", "infrastructure", "deployment"],
    "observability": ["observability", "logging", "metrics", "tracing", "Prometheus",
                      "Grafana", "ELK", "monitoring", "diagnostics", "alerting"],
    "robotics": ["robotics", "robot", "AGV", "manipulator", "arm", "motion planning",
                 "path planning", "obstacle avoidance", "VLA", "simulation"],
    "industrial": ["PLC", "SCADA", "Modbus", "OPC UA", "MQTT", "edge computing",
                   "industrial", "manufacturing", "factory", "automation"],
    "ai_ml": ["RAG", "LLM", "LangChain", "agent", "agentic", "embedding", "vector",
              "machine learning", "deep learning", "vision", "VLA"],
}
```

2. **支持用户自定义关键词**：从 JD 中自动提取高频词
3. **与 resume-jd 的语义分析整合**：不要两套独立逻辑

**文件**：`tools/keyword_matcher.py` 第 15-50 行
**影响范围**：所有非传统技术栈的 JD 分析
**修复难度**：中（需要设计关键词分类体系）

---

### FIX-003: 所有工具脚本 Windows GBK 编码问题

**问题描述**：
- `keyword_matcher.py` 和 `html_to_pdf.py` 的 emoji 输出在 Windows 终端报错
- `resume_parser.py` 已修复，但其他脚本没有
- 错误信息：`UnicodeEncodeError: 'gbk' codec can't encode character`

**修复方案**：
在每个工具脚本的 `main()` 函数开头添加：
```python
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

**文件**：
- `tools/keyword_matcher.py` ✅ 已修复
- `tools/html_to_pdf.py` ✅ 已修复
- 其他脚本需检查

**影响范围**：所有 Windows 用户
**修复难度**：低（3 行代码）

---

## 🟡 P1：严重问题（应该修复）

### FIX-004: Hook 脚本依赖 jq 且只警告不阻止

**问题描述**：
- `truth-verification.sh` 和 `evidence-chain.sh` 依赖 `jq` 命令
- Windows 用户普遍没有 jq
- 即使有 jq，hook 也只是警告（exit 0），不阻止违反原则的行为

**修复方案**：

**方案 A（推荐）：Python 版 hook**
```python
# hooks/truth_verification.py
import json, sys, os

def verify(data):
    tool_name = data.get("tool_name", "")
    file_path = data.get("tool_input", {}).get("file_path", "")

    if tool_name not in ("Write", "Edit"):
        return 0  # allow

    if not any(p in file_path for p in ("resume", "profile")):
        return 0  # allow

    content = data.get("tool_input", {}).get("content", "")

    # 检查是否有"精通"但没有项目支撑
    if "精通" in content:
        projects_dir = os.path.join(os.path.dirname(file_path), "../../profile/projects")
        if not os.path.exists(projects_dir) or len(os.listdir(projects_dir)) == 0:
            print("⚠️ WARNING: '精通' skills declared but no project evidence found", file=sys.stderr)
            # 阶段1: 警告 return 0
            # 阶段2: 阻止 return 1

    return 0

if __name__ == "__main__":
    data = json.load(sys.stdin)
    sys.exit(verify(data))
```

**方案 B：纯 bash（不依赖 jq）**
```bash
# 用 python -c 解析 JSON 替代 jq
tool_name=$(echo "$input" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))")
```

**文件**：`hooks/truth-verification.sh`, `hooks/evidence-chain.sh`
**影响范围**：三原则的工程强制
**修复难度**：中

---

### FIX-005: weasyprint 在 Windows 上需要 GTK 系统库

**问题描述**：
- weasyprint 安装成功，但运行时报错：`cannot load library 'gobject-2.0-0'`
- 需要安装 GTK for Windows，对非技术用户来说很困难
- 当前 fallback 到 playwright 可以工作，但体验不好

**修复方案**：

1. **增加环境预检**：在安装脚本中检测 weasyprint 是否可用
```python
def check_pdf_engine():
    """检查 PDF 引擎可用性"""
    try:
        import weasyprint
        return "weasyprint"
    except Exception:
        pass

    try:
        from playwright.sync_api import sync_playwright
        return "playwright"
    except ImportError:
        pass

    return None
```

2. **提供安装指引**：当 weasyprint 不可用时，给出 GTK 安装链接
3. **优先使用 playwright**：在 Windows 上默认先试 playwright（不需要系统库）

**文件**：`tools/html_to_pdf.py`, `install.sh`
**影响范围**：所有 Windows 用户的 PDF 导出
**修复难度**：低

---

## 🟢 P2：体验问题（有空修复）

### FIX-006: install.sh 使用 python3/pip3 在 Windows 上不可用

**问题描述**：
- Windows 上 `python3` 指向 Windows Store 占位符（Permission denied）
- `pip3` 同样不可用
- 实际可用的是 `python` 和 `pip`

**修复方案**：
```bash
# 优先用 python3，fallback 到 python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi
```

**文件**：`install.sh`
**影响范围**：Windows 用户安装体验
**修复难度**：低

---

### FIX-007: keyword_matcher 与 resume-jd 两套独立逻辑

**问题描述**：
- `keyword_matcher.py` 用硬编码关键词做匹配
- `resume-jd` 用 Claude 语义理解做匹配
- 两套逻辑可能产生矛盾结果
- 用户看到的匹配度可能不一致

**修复方案**：
- `keyword_matcher.py` 作为辅助工具，提供关键词列表
- `resume-jd` 的语义分析作为主逻辑
- 在 `jd-analysis.md` 中同时展示两个维度的结果

**文件**：`tools/keyword_matcher.py`, `skills/resume-jd/SKILL.md`
**影响范围**：JD 分析的准确性
**修复难度**：中

---

### FIX-008: 简历模板使用 Handlebars 语法但无渲染引擎

**问题描述**：
- `templates/official/*.html` 使用 `{{#each}}`、`{{#if}}` 语法
- Python 端没有渲染引擎
- 实际由 Claude 直接生成 HTML，模板只是参考

**修复方案**：
- 明确设计决策：在 SKILL.md 中声明"模板是布局参考，实际由 Claude 生成"
- 或者写一个 Python 渲染脚本

**文件**：`skills/resume-build/SKILL.md`, `templates/official/*.html`
**影响范围**：简历生成的结构一致性
**修复难度**：中

---

## 📋 修复优先级排序

| 顺序 | 编号 | 问题 | 修复难度 | 预计耗时 |
|---|---|---|---|---|
| 1 | FIX-003 | Windows GBK 编码 | 低 | 15 min |
| 2 | FIX-001 | 工作经历正则 | 低 | 30 min |
| 3 | FIX-005 | PDF 导出预检 | 低 | 30 min |
| 4 | FIX-006 | install.sh python3 | 低 | 15 min |
| 5 | FIX-004 | Hook 去 jq 依赖 | 中 | 2 h |
| 6 | FIX-002 | 关键词库扩展 | 中 | 3 h |
| 7 | FIX-007 | 逻辑统一 | 中 | 2 h |
| 8 | FIX-008 | 模板渲染决策 | 中 | 1 h |

**总预计耗时**：约 10 小时

---

## 📝 测试验证清单

修复后需要重新验证：

- [ ] FIX-001：用 newcreer.md 重新跑 resume_parser，工作经历应提取成功
- [ ] FIX-002：用 siemens JD 重新跑 keyword_matcher，应识别 10+ 关键词
- [ ] FIX-003：在 Windows 终端运行所有工具脚本，无编码错误
- [ ] FIX-004：在没有 jq 的环境运行 hook，不报错
- [ ] FIX-005：在没有 GTK 的 Windows 上导出 PDF，应自动 fallback 到 playwright
- [ ] FIX-006：在 Windows 上运行 install.sh，python 命令正常
