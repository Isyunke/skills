# 03 · 确定性工具层

> 凡是不需要 LLM "理解"或"创造"的事，都用 Python 代码做。
> LLM 只做：理解、共情、追问、改写、评分。

---

## 一、工具层总览

```
resume_alchemist/
  tools/
    __init__.py
    evidence_validator.py    # 证据链与原则校验
    match_scorer.py          # JD ↔ 候选人匹配度
    keyword_extractor.py     # JD 关键词抽取
    renderer.py              # data.yaml → HTML/MD/DOCX
    parser.py                # 简历文件 → data.yaml
    exporter.py              # HTML → PDF
    diff.py                  # 两份 yaml 的可解释 diff
    migrate.py               # v1 → v2 迁移
    i18n.py                  # 字段级本地化
    roi_analyzer.py          # outcomes.yaml → 反馈洞察
    state_builder.py         # 从 KB 派生 .resume-state.json
    io_utils.py              # 原子写、锁
    schemas/                 # Pydantic v2 models
      __init__.py
      identity.py
      project.py
      jd.py
      resume.py
      outcomes.py
```

每个工具的 contract：

```python
# 通用 contract
def tool_fn(input_path: Path, **kwargs) -> ToolResult:
    """
    - 纯函数：相同输入 → 相同输出
    - 副作用只限于写自己负责的输出文件
    - 错误用 raised exception，不静默 fail
    - 返回 ToolResult（含 success/data/warnings）
    """
```

且每个工具都暴露三种调用方式：

| 调用方式 | 用途 |
|---|---|
| Python API | 其他工具组合调用、单元测试 |
| CLI 子命令 | 用户/CI 直接跑：`resume validate ./profile/projects/proj-001/` |
| MCP tool | 暴露给任何 agent：`mcp.resume.validate` |

---

## 二、`evidence_validator.py` —— 取代 hooks/*.sh

### 职责

校验**三条不可妥协原则**是否被遵守。**v1 的两个 bash hook 全部废弃**。

### 输入

```python
ValidatorInput(
    profile_path: Path,        # profile/ 根目录
    resume_path: Optional[Path] = None,  # 单份简历 yaml
    jd_path: Optional[Path] = None,
    strict: bool = True,       # strict 模式下违规 raise，非 strict 模式只警告
)
```

### 输出

```python
class ValidationResult(BaseModel):
    passed: bool
    principle_results: dict[str, PrincipleResult]
    # principle_results 的 key: "truth_first" / "evidence_chain" / "targeted_for_jd"
    violations: list[Violation]
    warnings: list[Warning]

class Violation(BaseModel):
    principle: Literal["truth_first", "evidence_chain", "targeted_for_jd"]
    severity: Literal["error", "warning"]
    location: str               # 例如 "skills/data.yaml#categories[0].skills[1]"
    message_zh: str
    message_en: str
    actionable_fix: str         # 必须给出修复建议，不是只说"违规"
```

### 检查规则

#### 真实性原则
- ✅ 所有 `proj-XXX` 必须有 `data.yaml`（不能引用空气）
- ✅ `verified_by: code_trace` 的项目必须有 `verification_score`
- ✅ `achievements` 的每一项必须有 `source`（不能凭空给数字）
- ✅ 简历 `sections.experience.entries[].achievements[].source_project` 必须能解析到真实项目

#### 证据链原则
- ✅ `proficiency: expert` 必须有 ≥2 个项目 + ≥1 个量化成果
- ✅ `proficiency: proficient` 必须有 ≥1 个项目
- ✅ 简历中出现的技能必须存在于 `skills/data.yaml` 中
- ✅ `evidence_strength` 由 validator 计算，不允许用户手填覆盖

#### 针对性原则
- ✅ 每份 `resume-v<N>.yaml` 必须有 `jd_id` 字段
- ✅ 简历 keyword 覆盖率必须 ≥ 60%（否则警告"不针对"）
- ✅ 不允许多个 JD 复用同一个 `resume-v<N>.yaml`

### CLI

```bash
# 校验整个项目
resume validate

# 只校验一份简历
resume validate --resume resumes/jd-001-xx/resume-v1.yaml

# 校验某个原则
resume validate --principle evidence_chain

# 非 strict 模式：只报告，不阻断
resume validate --no-strict
```

### 退出码

| code | 含义 |
|---|---|
| 0 | 全部通过 |
| 1 | 有 error（违规） |
| 2 | 只有 warning |
| 3 | KB 损坏（schema 解析失败） |

### 何处自动调用

| 调用方 | 时机 |
|---|---|
| `resume build` | 渲染 HTML 前必跑，failed 则阻断渲染 |
| `resume export` | 导出 PDF 前必跑 |
| MCP server | 任何写 KB 的 tool 完成后自动跑 |
| git pre-commit hook | 可选：用户安装后每次提交校验 |

---

## 三、`match_scorer.py` —— 取代 keyword_matcher.py

### 职责

输入 `jd.yaml` + `profile/`，输出 `match-report.yaml`。

### 算法（分层 fallback）

```python
def score(jd: JD, profile: Profile) -> MatchReport:
    # Layer 1: 关键词匹配（确定性，必须可用）
    keyword_score = keyword_match(jd.keywords, profile.flatten_keywords())

    # Layer 2: 证据链强度评估（确定性）
    evidence_score = evidence_strength_check(jd, profile)

    # Layer 3: 量化数据覆盖率（确定性）
    quant_score = quantification_ratio(profile)

    # Layer 4: STAR 完整度（确定性）
    star_score = star_completeness_ratio(profile)

    # Layer 5: 经验等级匹配（确定性）
    level_score = experience_level_fit(jd, profile)

    # Layer 6 [optional]: 语义嵌入相似度
    if SEMANTIC_AVAILABLE:
        semantic_score = embedding_similarity(jd, profile)
    else:
        semantic_score = None

    return MatchReport(
        overall=weighted_sum(...),
        dimensions={...},
        gaps=identify_gaps(jd, profile),
        recommendations=generate_recommendations(...),
    )
```

### 关键词匹配优于 v1 的点

| v1 | v2 |
|---|---|
| 硬编码 150 关键词 | 用户可扩展 `keywords/<industry>.yaml` |
| 不分行业 | 行业词包：tech / product / design / sales / ... |
| 不分权重 | JD 中越靠前/越频繁的关键词权重越高 |
| 同义词不识别 | `keywords.yaml` 支持 `aliases: [K8s, Kubernetes, k8s]` |
| 大小写敏感 | 全部 normalize |

### 行业词包文件

```
resume_alchemist/data/keywords/
  tech.yaml          # 编程、框架、devops、AI
  product.yaml       # PRD、用研、增长、AB 测试
  design.yaml        # Figma、设计系统、用研、视觉
  sales.yaml         # 渠道、客户成功、CRM、增长
  ...
```

```yaml
# tech.yaml 示例
schema_version: "2.0"
schema_type: "keyword_pack"
industry: tech

categories:
  programming_languages:
    - canonical: Python
      aliases: [py, python3]
      weight_base: 1.0
    - canonical: Go
      aliases: [golang, Go-lang]
      weight_base: 1.0

  frameworks:
    - canonical: Kubernetes
      aliases: [K8s, k8s, kube]
      weight_base: 0.9
```

### 可选：语义嵌入

```bash
# 默认不安装（保持轻量）
pip install resume-alchemist

# 想用语义嵌入：
pip install resume-alchemist[semantic]   # 安装 sentence-transformers
```

未安装时，`match_scorer` 自动跳过语义层，全靠确定性算法，**功能不缺**，只是没有"语义相似"的加分项。

---

## 四、`renderer.py` —— 真·模板引擎

### 职责

`data.yaml` + Jinja2 template → HTML / Markdown / DOCX

### 反 v1 模式：明确分工

| v1 反模式 | v2 |
|---|---|
| LLM 拼 HTML | Jinja2 渲染 |
| 模板里写 `{{#each}}`（Handlebars） | 统一 Jinja2 |
| CSS 内联在 HTML | CSS 与模板分离 + build 时内联 |
| 字段名靠 LLM 猜 | 用 Pydantic model dict() 喂给模板 |

### 模板组织

```
templates/
  official/
    resume/
      tech-standard/
        template.html.j2
        style.css
        meta.yaml           # 模板元数据：名称、适合行业、是否双语
      tech-modern/
        template.html.j2
        style.css
        meta.yaml
      product-standard/
        ...
    narrative/             # 用于 yaml → md 渲染
      project.md.j2
      jd.md.j2
      interview-guide.md.j2
  user/                    # 用户自定义
```

### 模板必须支持的字段集

由 schema 决定（详见 [02-data-layer-spec.md](02-data-layer-spec.md)），模板里通过 `data.sections[]` 迭代渲染。

### CLI

```bash
resume render \
  --data resumes/jd-001/resume-v1.yaml \
  --template tech-modern \
  --output resumes/jd-001/resume-v1.html

# 渲染所有 narrative（项目叙事文档）
resume render --all-narratives

# 预览（不写文件，stdout）
resume render --data ... --preview
```

### 内嵌 CSS

```python
def render(data_path, template_dir, output_path):
    template = jinja_env.get_template(f"{template_dir}/template.html.j2")
    css = (Path(template_dir) / "style.css").read_text()
    html = template.render(data=data, css_inline=css)
    atomic_write(output_path, html)
```

模板里：

```html
<style>{{ css_inline }}</style>
```

这样 PDF 导出（weasyprint / playwright）不会丢样式。

---

## 五、`parser.py` —— 升级 resume_parser.py

### 职责

把 `.pdf / .docx / .md / .html / .txt` 简历解析为 `data.yaml` 草稿（让用户后续 review）。

### 关键改进

| v1 | v2 |
|---|---|
| 纯正则 | 多段 pipeline：基础提取 → LLM 辅助归一化 → 用户确认 |
| 输出 markdown | 输出 `parsed-draft.yaml`，需要 `resume intake confirm` 后才入 KB |
| 多栏排版易失败 | pdfplumber 用 layout 模式 + 兜底用 OCR |
| 中文公司识别差 | NER + 自定义中文公司名词典 |

### Pipeline

```
PDF/DOCX
  ↓ [pdfplumber / python-docx]
原始文本 (with layout hints)
  ↓ [section detector — 用正则识别 经验/教育/技能 section]
section 文本块
  ↓ [field extractor — 各 section 各自提取]
parsed-draft.yaml (字段可能不完整或不准)
  ↓ [可选：LLM-assisted enrichment — 把"前端开发"映射到 canonical role]
parsed-draft.yaml (enriched)
  ↓ [validator — 跑 evidence_validator 但只警告]
final draft
  ↓ [用户在 agent 里 confirm]
入 KB
```

### Confirm 阶段（人在回路）

```
agent: 我从你的简历里提取了 3 段经历、12 项技能。
        但有 2 处不确定：
        1. "Smartcoin Tech" 是公司名还是项目名？
        2. "用 Python 开发了 XX" —— 这是 proj-001 还是 proj-002？
        请逐个确认。
```

---

## 六、`exporter.py` —— 升级 html_to_pdf.py

### 改进

1. **环境预检**：`resume export --check` 列出可用引擎、给出安装指引
2. **优先级**：Windows → playwright；Linux/Mac → weasyprint；都不行 → 报错并提示
3. **PDF 后处理**：可选嵌入字体（解决面试官打开字体不一致问题）
4. **分页控制**：渲染时用 CSS `page-break-inside: avoid` 配合 `print` media query

### CLI

```bash
resume export --resume resumes/jd-001/resume-v1.html --format pdf
resume export --check
resume export --engine playwright    # 强制引擎
```

---

## 七、`diff.py` —— v2 新增

### 职责

比较两份 `data.yaml`（同实体两个版本），给出**人类友好的语义 diff**。

```bash
resume diff resumes/jd-001/resume-v1.yaml resumes/jd-001/resume-v2.yaml
```

输出：

```
📊 Resume v1 → v2 (jd-001-xx公司后端)

  + 新增了 1 个项目：proj-005-AI 推荐系统
  ~ 修改了 summary：
      - 4 年互联网后端经验...
      + 4 年互联网后端 + AI 推荐系统经验...
  ~ 调整了 skills.programming.Python：
      proficiency: proficient → expert
      原因：新增 proj-005 作为证据，符合 expert 的要求
  - 删除了不相关的项目：proj-002（与本 JD 关联度低）

✅ 校验：通过
📈 匹配度：72 → 81 (+9)
```

### 用途

- `resume optimize` 时给用户看"我改了啥，为什么"
- v1 → v2 迁移时让用户看清变化
- 多版本简历对比（哪个版本响应率最高）

---

## 八、`migrate.py` —— v1 → v2

详见 [08-migration-v1-to-v2.md](08-migration-v1-to-v2.md)。这里只列契约：

```bash
resume migrate                # 默认迁移到最新版本
resume migrate --dry-run      # 只报告，不写
resume migrate --backup-dir .resume-backup-v1
resume migrate --from 1.3 --to 2.0
```

---

## 九、`i18n.py` —— 取代 resume-localize 内嵌逻辑

### 职责

不只是翻译——是**文化适配**。

### 流程

```
中文 data.yaml
  ↓ [field-level translate — 调用 LLM]
英文 data.yaml (字面翻译)
  ↓ [cultural adapter — 应用文化规则]
英文 data.yaml (适配后)
  ↓ [terminology normalizer — 把"精通"→"Expert"等]
英文 data.yaml (最终)
```

### 文化规则示例

```yaml
# resume_alchemist/data/locales/en-US/rules.yaml
remove_fields:
  - identity.photo            # 美式简历不放照片
  - identity.contact.gender
  - identity.contact.age
  - identity.contact.political_affiliation

reformat:
  date_format: "MMM YYYY"     # "2024.01" → "Jan 2024"
  summary_max_sentences: 2
  achievement_starts_with_action_verb: true

style:
  use_action_verbs: true       # "负责" → "Led"
  quantify_required: strict
```

### CLI

```bash
resume i18n --target en-US                    # 全档案本地化
resume i18n --target en-US --resume jd-001    # 仅本份简历
```

---

## 十、`roi_analyzer.py` —— v2 新增·关键

### 职责

输入：所有 `resumes/*/outcomes.yaml`
输出：`.resume-cache/derived/roi-report.yaml` + 给 `resume status` 用

### 计算

```python
class RoiReport(BaseModel):
    period: str  # "last_30d" / "all_time"

    funnel:
        submitted: int
        responded: int                  # 收到任何回应
        interview_invited: int
        interview_passed_round_1: int
        offer_received: int
        offer_accepted: int

    conversion_rates:
        submit_to_response: float        # 例 0.42
        response_to_invitation: float
        invitation_to_offer: float

    best_performing_resumes: list[dict]  # 按响应率排序
        # [{resume_id, jd_id, response_rate, score}]

    common_weak_spots: list[dict]
        # [{topic, mentioned_count, suggested_action}]

    channels_effectiveness: dict[str, float]
        # {"拉勾": 0.55, "Boss": 0.30, ...}
```

### 用途

- `resume status` 显示 dashboard
- `coach` 在生成下一份简历时考虑历史信号

---

## 十一、`state_builder.py` —— `.resume-state.json` 派生

v2 中 `.resume-state.json` 不再是事实来源，每次需要时从 KB 重建：

```python
def build_state(project_root: Path) -> ResumeState:
    return ResumeState(
        schema_version="2.0",
        identity=load_yaml(project_root / "profile/identity.yaml"),
        counts=Counts(
            projects=count_dirs(project_root / "profile/projects/"),
            skills=count_skills(project_root / "profile/skills/data.yaml"),
            jds=count_dirs(project_root / "resumes/"),
            resumes=count_files(project_root / "resumes/", pattern="resume-v*.yaml"),
        ),
        timestamps=collect_timestamps(...),
        active_jd_id=detect_active_jd(...),
        roi_summary=roi_analyzer.summary(),
    )
```

调用：

- `resume status` 显示前重建
- 任何 MCP tool 调用前重建（保证状态新鲜）

---

## 十二、工具间调用图

```
parser ────────────────┐
                       ↓
intake-skill ────→ data.yaml (drafts)
                       ↓
              evidence_validator ←─── schemas/
                       ↓
              renderer (narrative.md)
                       ↓
                       │
match-skill ────→ keyword_extractor ────→ jd.yaml
                       ↓
                  match_scorer
                       ↓
                  match-report.yaml

output-skill ────→ renderer (resume.html)
                       ↓
                  evidence_validator (final gate)
                       ↓
                  exporter (PDF)

feedback-skill ──→ outcomes.yaml
                       ↓
                  roi_analyzer
                       ↓
                  state_builder.refresh()
```

**单向依赖**，任何工具都可独立单测。

---

## 十三、测试策略

每个工具：

| 测试类型 | 覆盖率目标 |
|---|---|
| 单元测试（fixtures + assert） | ≥ 90% |
| Schema round-trip 测试（yaml → model → yaml） | 100% |
| CLI 测试（subprocess + 退出码） | 主流程 100% |
| Golden file 测试（renderer 输出对比） | 100% |

整体：

| 测试类型 | 覆盖 |
|---|---|
| E2E 旅程测试 | 5 个（对应 5 阶段闭环） |
| MCP server 集成测试 | 跑通 5 阶段 |
| 跨平台测试 | Windows / macOS / Linux 至少 CI 三套 |

---

下一章：[04-mcp-cross-agent.md](04-mcp-cross-agent.md) — 跨 agent 接入
