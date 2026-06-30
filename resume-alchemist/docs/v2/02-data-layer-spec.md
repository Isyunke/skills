# 02 · 知识档案层（KB）规范

> 这是 v2 的地基。一旦 schema 定下来，上面所有工具、Skill、模板都基于它。
> 设计原则：**严格 schema + 双轨制（yaml/md）+ 向后兼容 + 互操作（JSON Resume）**

---

## 一、设计决策概要

| 决策 | 选择 | 理由 |
|---|---|---|
| 结构化格式 | **YAML** | 比 JSON 易读，比 TOML 表达力强，注释友好 |
| Schema 校验 | **Pydantic v2** | Python 生态最稳，自动生成 JSON Schema |
| 叙事格式 | **Markdown** | 人类可读、git diff 友好 |
| 关系 | **yaml 是事实，md 是渲染产物** | 单一事实来源，避免漂移 |
| 互操作 | **JSON Resume v1.2.1** 子集 | 业界标准，能被其他工具消费 |
| 多语言 | 字段级 `_zh` / `_en` 后缀 | 避免目录分裂 |
| 版本 | 每个 yaml 顶部带 `schema_version: 2.0` | 强制可演进 |

---

## 二、KB 目录结构

```
<user-resume-project>/
├── .resume-state.json            # 派生 cache（v2 不再是事实来源）
├── .resume-state.lock            # 写锁
├── .resume-cache/                # 临时文件，不入 git
│   ├── traces/                   # LLM 调用日志（脱敏）
│   └── derived/                  # 派生统计的缓存
├── .resume-backup-v1/            # 迁移时备份的 v1 原始数据（不入 git）
│
├── profile/
│   ├── identity.yaml             # 基本信息（姓名、联系方式等）
│   ├── self-profile/
│   │   ├── data.yaml             # 个人总结 + 教育 + 软技能
│   │   └── narrative.md          # 渲染产物
│   ├── skills/
│   │   └── data.yaml             # 技能树（详见 §4.2）
│   ├── projects/
│   │   └── proj-001-xxx/
│   │       ├── data.yaml         # 项目结构化数据
│   │       ├── narrative.md      # 项目叙事
│   │       └── evidence/         # 真凭实据
│   │           ├── commits.yaml  # commit 链接清单
│   │           ├── metrics.yaml  # 量化数据出处
│   │           └── *.png         # 截图等
│   └── work-history/
│       └── company-001-xxx/
│           ├── data.yaml
│           └── narrative.md
│
├── resumes/
│   └── jd-001-xxx/
│       ├── jd.yaml               # JD 解析结果
│       ├── jd-analysis.md        # 渲染产物
│       ├── match-report.yaml     # 匹配度报告（detailed）
│       ├── resume-v1.yaml        # 简历数据（不是 HTML）
│       ├── resume-v1.html        # HTML 渲染产物
│       ├── resume-v1.pdf         # PDF 导出
│       ├── interview-guide.yaml
│       ├── interview-guide.md
│       └── outcomes.yaml         # 投递结果（v2 新增）
│
├── learning/
│   └── skill-001-xxx/
│       ├── plan.yaml             # 学习计划结构化
│       └── plan.md
│
└── templates/                    # 用户自定义模板（与 skill 包的 templates/ 区分）
    └── user/
        └── my-template.html.j2
```

**关键变化对 v1**：

- `profile/projects/proj-001.md` → `profile/projects/proj-001-xxx/data.yaml + narrative.md`（升级为目录）
- `self-profile.md` → 拆为 `identity.yaml` + `skills/data.yaml` + `self-profile/data.yaml`（按职责）
- `.resume-state.json` 从"事实"降级为"派生 cache"
- 每个 JD 目录新增 `outcomes.yaml`

---

## 三、核心 Schema 速览（详细字段在 §4）

| 文件 | Pydantic model | 关键字段 |
|---|---|---|
| `identity.yaml` | `Identity` | name, contact, target_role, location |
| `skills/data.yaml` | `SkillTree` | skills[]（含 evidence_strength） |
| `projects/<id>/data.yaml` | `Project` | id, role, period, star, tech_stack, achievements |
| `work-history/<id>/data.yaml` | `WorkExperience` | company, role, period, achievements |
| `resumes/<jd>/jd.yaml` | `JobDescription` | company, role, requirements[]（含 priority） |
| `resumes/<jd>/match-report.yaml` | `MatchReport` | dimensions, gaps, recommendations |
| `resumes/<jd>/resume-v<N>.yaml` | `Resume` | sections[], composed_from_projects[] |
| `resumes/<jd>/outcomes.yaml` | `Outcomes` | events[]（append-only） |

---

## 四、Schema 详细定义

### 4.1 `identity.yaml`

```yaml
schema_version: "2.0"
schema_type: "identity"

name:
  zh: 张三
  en: Zhang San
contact:
  email: zs@example.com
  phone: "+86-13800000000"
  location: 北京
  links:
    - type: github
      url: https://github.com/zhangsan
    - type: linkedin
      url: https://linkedin.com/in/zhangsan
target:
  role: 后端工程师
  industry: 互联网
  experience_level: "3-5y"      # enum: fresh / 1-3y / 3-5y / 5y+
  preferred_locations: [北京, 上海]
locale_preference: zh-CN
```

Pydantic（伪代码）：

```python
class Identity(BaseModel):
    schema_version: Literal["2.0"]
    schema_type: Literal["identity"]
    name: LocalizedString
    contact: Contact
    target: TargetPosition
    locale_preference: str = "zh-CN"
```

### 4.2 `skills/data.yaml`（技能树）

```yaml
schema_version: "2.0"
schema_type: "skill_tree"

categories:
  - id: programming
    label_zh: 编程语言
    label_en: Programming Languages
    skills:
      - name: Python
        proficiency: expert       # enum: known / proficient / expert
        evidence_strength: strong # enum: none / weak / strong (computed)
        score: 8                  # 1-10 self-rating
        evidence:
          projects: [proj-001, proj-003]
          years_of_use: 5
          last_used: "2024-06"
        keywords_zh: [Python, 异步, asyncio]
        keywords_en: [Python, asyncio]

  - id: databases
    label_zh: 数据库
    skills:
      - name: PostgreSQL
        proficiency: proficient
        evidence_strength: strong
        evidence:
          projects: [proj-001]
```

**关键规则（由 `evidence_validator` 强制）**：

| 声明 | 必需证据 |
|---|---|
| `proficiency: expert` | 至少 2 个 project 引用 + 至少 1 个量化成果 |
| `proficiency: proficient` | 至少 1 个 project 引用 |
| `proficiency: known` | 无强制 |
| `evidence_strength: strong` | 由 validator 计算，**不允许用户手填** |

### 4.3 `projects/<id>/data.yaml`（核心：项目）

```yaml
schema_version: "2.0"
schema_type: "project"

id: proj-001-xx系统性能优化
created_at: "2026-06-13T10:00:00+08:00"
verified_by: code_trace         # enum: dialog / file_import / code_trace
verification_score: 92          # 0-100, only when verified_by=code_trace

meta:
  name_zh: XX 系统性能优化
  name_en: Performance optimization for XX system
  period:
    start: "2024-01"
    end: "2024-06"
  role: 后端核心开发
  team_size: 5
  company: 某互联网公司
  links:
    - type: code
      url: https://github.com/zhangsan/xx-system
      private: true
    - type: doc
      url: https://internal-wiki/...

star:
  situation: |
    XX 系统是公司核心业务系统，日活 100w+，但 P99 响应时间 800ms 影响下单转化。
  task: |
    我负责性能优化模块，目标把 P99 从 800ms 降到 200ms 以内。
  action: |
    1. 用 Py-Spy 定位瓶颈：80% 时间花在数据库慢查询
    2. 引入 SQL 慢查询分析 + 索引重建
    3. 引入 Redis 二级缓存，热点 key 命中率 95%+
    4. 异步化非关键路径
  result: |
    P99 从 800ms 降到 150ms（下降 81%），下单转化率提升 12%

tech_stack:
  primary: [Python, FastAPI, PostgreSQL, Redis]
  secondary: [Docker, K8s, Prometheus]

skills_used:
  - name: Python
    proficiency_demonstrated: expert
    note: "全流程异步化重构"
  - name: PostgreSQL
    proficiency_demonstrated: proficient
    note: "慢查询优化 + 索引设计"

achievements:
  - type: performance
    metric: "P99 latency"
    before: "800ms"
    after: "150ms"
    delta: "-81%"
    source: "Prometheus 监控截图"   # 必须可溯源
  - type: business
    metric: "下单转化率"
    before: "3.2%"
    after: "3.6%"
    delta: "+12%"
    source: "BI 报表"

interview_prep:
  biggest_challenge: "热点 key 雪崩问题如何避免"
  solution_summary: "用 redis lua 脚本 + 互斥锁 + 二级 fallback"
  lessons_learned:
    - "性能瓶颈不要靠猜，先 profile"
    - "缓存的边界条件比缓存本身更重要"
  if_redo: "一开始就引入分布式追踪，能少走 2 周弯路"

# 由 evidence_validator 计算，用户不要手写
_computed:
  has_quantified_achievement: true
  has_star_complete: true
  evidence_files_count: 3
```

### 4.4 `resumes/<jd>/jd.yaml`（JD 解析）

```yaml
schema_version: "2.0"
schema_type: "jd"

id: jd-001-xx公司后端
created_at: "2026-06-13T10:00:00+08:00"
source:
  type: paste       # enum: paste / url / file
  raw_text: |
    [原始 JD 文本]
  url: null

meta:
  company: XX 公司
  role: 后端工程师
  salary_range: "25-40k"
  location: 北京
  level: P6

requirements:
  - id: req-1
    text_zh: 精通 Python，3 年以上经验
    text_en: Expert in Python, 3+ years
    priority: must_have       # enum: must_have / nice_to_have / bonus
    keywords: [Python, asyncio, 性能优化]
    category: programming_language

  - id: req-2
    text_zh: 熟悉分布式系统
    priority: must_have
    keywords: [分布式, 一致性, CAP, Raft]
    category: architecture

  - id: req-3
    text_zh: 有 K8s 经验
    priority: nice_to_have
    keywords: [Kubernetes, K8s, Helm]
    category: devops

extracted_keywords:           # 由 keyword_extractor 工具产出
  all:
    - {term: Python, weight: 1.0, source: req-1}
    - {term: 分布式, weight: 1.0, source: req-2}
    - {term: K8s, weight: 0.6, source: req-3}
  top_n: 10                   # 前 N 个用于简历高亮
```

### 4.5 `resumes/<jd>/match-report.yaml`（匹配度报告）

```yaml
schema_version: "2.0"
schema_type: "match_report"

jd_id: jd-001-xx公司后端
generated_at: "2026-06-13T10:00:00+08:00"
generated_by: tools/match_scorer.py v2.0

overall:
  score: 72        # 0-100
  verdict: "强候选"  # 跑出来的判断: 强候选 / 可投递 / 风险高 / 不建议

dimensions:
  keyword_coverage:
    score: 80
    weight: 0.3
    detail:
      matched:    [Python, FastAPI, Redis, PostgreSQL]
      partial:    [分布式]              # 有但弱证据
      missing:    [K8s, Kafka]
  evidence_chain:
    score: 90
    weight: 0.3
    detail:
      strong_evidence_skills_used: 6
      weak_evidence_skills_used: 1
      no_evidence_claims: 0           # 必须为 0，否则违反原则
  quantification:
    score: 75
    weight: 0.2
    detail:
      quantified_achievements: 5
      total_achievements: 7
      ratio: 0.71
  star_completeness:
    score: 60
    weight: 0.1
    detail:
      complete_star_projects: 2
      partial_star_projects: 1
      missing_action_details: [proj-002]
  experience_level_fit:
    score: 85
    weight: 0.1
    detail:
      jd_required: "3-5y"
      candidate_actual: "4y"
      verdict: 匹配

gaps:
  critical:
    - skill: K8s
      priority: must_have_but_missing
      recommendation: "短期内难补，考虑用 Docker + Compose 经验铺垫；中长期推荐 resume learn K8s"
  important:
    - skill: 分布式系统
      priority: must_have_but_weak
      recommendation: "你的 proj-002 有部分经验但未量化，建议在简历中突出 Saga 模式落地"

recommendations:
  for_resume:
    - "把 proj-001 的缓存设计描述加入'分布式'关键词"
    - "P99 改为'P99 latency'让英文 ATS 能识别"
  for_interview:
    - "准备 K8s 基础题（即使简历不写，HR 可能问）"
  for_learning:
    - {skill: K8s, urgency: high, estimated_hours: 40}
```

### 4.6 `resumes/<jd>/resume-v<N>.yaml`（简历数据）

```yaml
schema_version: "2.0"
schema_type: "resume"

id: resume-v1
jd_id: jd-001-xx公司后端
created_at: "2026-06-13T10:00:00+08:00"
template: tech-modern        # 决定 render 时用哪个 Jinja2 模板
locale: zh-CN

# 简历内容（结构化）
sections:
  - type: header
    name: 张三
    role_title: 后端工程师 - 应聘 XX 公司
    contact:
      email: zs@example.com
      phone: "+86-138..."
      location: 北京
      links:
        - {label: GitHub, url: https://github.com/zhangsan}

  - type: summary
    content: |
      4 年互联网后端经验，专注高并发性能优化。
      在 XX 公司主导核心系统性能改造，P99 降低 81%，
      下单转化率提升 12%。

  - type: skills
    groups:
      - label: 编程语言
        items: [Python (精通), Java (熟练)]
      - label: 框架
        items: [FastAPI (精通), Django (熟练)]

  - type: experience
    entries:
      - company: 某互联网公司
        role: 后端核心开发
        period: "2022.01 - 2024.06"
        achievements:
          - text: "主导 XX 系统性能改造，P99 从 800ms→150ms"
            source_project: proj-001     # 必须可追溯
          - text: "搭建监控告警体系，故障定位时间从 30min→5min"
            source_project: proj-002

  - type: projects
    entries:
      - source_project: proj-001          # 引用 KB 中的真实项目
        emphasis: full                    # full / brief
      - source_project: proj-003
        emphasis: brief

# 验证元数据（render 前必须通过）
_validation:
  passed: true
  passed_at: "2026-06-13T10:05:00+08:00"
  validator_version: 2.0
  checks:
    truth_first: pass
    evidence_chain: pass
    targeted_for_jd: pass
```

### 4.7 `resumes/<jd>/outcomes.yaml`（v2 新增·关键）

```yaml
schema_version: "2.0"
schema_type: "outcomes"

jd_id: jd-001-xx公司后端
resume_used: resume-v1.yaml

# Append-only event log
events:
  - id: evt-001
    timestamp: "2026-06-14T09:00:00+08:00"
    type: submitted
    detail:
      channel: 拉勾网         # 投递渠道
      method: 公司官网
      notes: "通过内推链接投递"

  - id: evt-002
    timestamp: "2026-06-16T15:30:00+08:00"
    type: response
    detail:
      response_type: interview_invitation
      delay_hours: 54

  - id: evt-003
    timestamp: "2026-06-18T14:00:00+08:00"
    type: interview
    detail:
      round: 1
      type: technical          # technical / behavioral / system_design / hr / final
      duration_minutes: 60
      result: passed           # passed / rejected / pending
      interviewer_feedback: "Python 基础扎实，分布式系统答得一般"
      questions_struggled_with:
        - "Raft 协议的 leader election"
        - "K8s service 和 ingress 的区别"

  - id: evt-004
    timestamp: "2026-06-25T10:00:00+08:00"
    type: final_result
    detail:
      outcome: offer            # offer / rejected / withdrew
      offer_details:
        salary_total: "35k * 16"
        accepted: false
        decline_reason: "另一家 base 更高"

# 由 tools/roi_analyzer.py 派生（不要手写）
_computed:
  total_days_to_close: 14
  rounds_passed: 1
  weak_spots: [Raft, K8s_networking]
```

---

## 五、双轨制：data.yaml → narrative.md 的渲染规则

每次 `data.yaml` 变化时，自动重新渲染对应的 `narrative.md`：

```python
# tools/renderer.py 内部逻辑
def regenerate_narrative(yaml_path: Path) -> None:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    schema_type = data["schema_type"]
    template_path = TEMPLATES[schema_type]  # 例如 "templates/narrative/project.md.j2"
    rendered = jinja2_render(template_path, data=data)
    md_path = yaml_path.with_name("narrative.md")
    atomic_write(md_path, rendered)
```

**纪律**：
- `narrative.md` 顶部加一行 `<!-- AUTOGENERATED FROM data.yaml — DO NOT EDIT -->`
- 用户改了 `narrative.md` 但没改 `data.yaml` → 下次渲染会覆盖；validator 会警告
- 用户想改文案 → 改 `data.yaml` 的字段或者改模板

---

## 六、JSON Resume 互操作

提供双向转换：

```bash
resume export --format json-resume > resume.json
resume import --format json-resume resume.json
```

字段映射表（节选）：

| v2 KB | JSON Resume |
|---|---|
| `identity.name.zh / .en` | `basics.name` |
| `identity.contact.email` | `basics.email` |
| `projects/<id>/data.yaml` | `projects[]` 项 |
| `skills/data.yaml.categories[].skills[]` | `skills[].keywords[]` |
| `work-history/<id>/data.yaml` | `work[]` 项 |

**好处**：用户的档案可以直接被 [JSON Resume 主题](https://jsonresume.org/themes/)渲染，可以被 LinkedIn 等工具消费。

---

## 七、原子写与并发安全

```python
# tools/io_utils.py
def atomic_write_yaml(path: Path, data: dict) -> None:
    """yaml 原子写 + flock"""
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10):
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp_path, path)   # atomic on POSIX & Windows
```

---

## 八、Schema 版本与迁移

| 版本 | 状态 | 兼容性 |
|---|---|---|
| 1.x | v1 系列 | v2 工具能读、能 migrate，但不能直接消费 |
| 2.0 | v2 当前 | LTS |
| 2.x | 加字段不破坏 | 自动兼容 |
| 3.0 | 破坏性 | 必须走 `resume migrate` |

每个 yaml 文件首行 `schema_version: "2.0"` 是必须的。读 yaml 的工具必须先 check 版本：

```python
if data.get("schema_version") != "2.0":
    raise SchemaVersionError(f"Need migrate: {path}")
```

详见 [08-migration-v1-to-v2.md](08-migration-v1-to-v2.md)。

---

下一章：[03-tools-layer-spec.md](03-tools-layer-spec.md) — 确定性工具层
