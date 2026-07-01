# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.0] - 2026-07-01

> **v2 preview release · P0 · foundation layer.**
> Backward compatible with 1.3.x: existing Claude Code users see no
> behavior change unless they explicitly invoke the new tools. The v1
> triggers, workflows, and file layout are fully preserved. See
> [docs/v2/README.md](docs/v2/README.md) for the full v2 plan.

### Added

#### Tools layer (v2 foundation)
- **`tools/schemas/`**: Pydantic v2 strict schemas for every KB entity
  (identity, skills, project, jd, resume, outcomes, state) with shared
  `SCHEMA_VERSION = "2.0"` and `SchemaVersionError` for migrate routing.
- **`tools/io_utils.py`**: cross-platform atomic writes, cross-process
  filelock (`file_lock` / `locked_edit_yaml`), consistent YAML/JSON
  loaders with schema-version awareness.
- **`tools/evidence_validator.py`**: real, blocking enforcement of the
  three non-negotiable principles (truth_first / evidence_chain /
  targeted_for_jd). Every violation ships a `fix` hint following the
  What/Why/How template. CLI: `python -m tools.evidence_validator`.
- **`tools/state_builder.py`**: derives `.resume-state.json` from the KB
  on demand; preserves `initialized_at` and pinned `active_jd_id` across
  rebuilds. CLI: `python -m tools.state_builder`.

#### Data assets
- **`tools/data/keywords/{tech,product,design}.yaml`**: externalised
  industry keyword packs with `canonical` + `aliases` + per-term weight.
  User-extensible without code changes.

#### Testing / CI
- 6 new test modules under `tests/`: schemas, io_utils, evidence
  validator, state builder, keyword matcher, CLI smoke tests.
- **130 tests · 92.1% coverage** (see `.coveragerc` for scope).
- GitHub Actions CI matrix: Ubuntu/Windows/macOS × Python 3.9/3.11/3.12,
  plus a keyword-pack YAML sanity job.

#### Documentation
- **`docs/v2/`**: 10-chapter refactor plan (vision, 7-layer
  architecture, data spec, tools spec, MCP cross-agent, skill redesign,
  feedback loop, UX improvements, migration, roadmap).

### Changed

#### `tools/keyword_matcher.py` (rewritten, backward compatible)
- Keyword pack now loaded from `tools/data/keywords/<industry>.yaml`
  instead of a hardcoded dict.
- Aliases (`K8s` ↔ `Kubernetes`, `高并发` ↔ `High Concurrency`, ...)
  are resolved to the canonical form on extraction.
- Added `--industry`, `--json`, `--list-industries` CLI flags.
- New `weighted_coverage` metric; `coverage` retained for compatibility.
- Legacy `DOMAIN_KEYWORDS` module attribute rebuilt from the tech pack
  so existing importers keep working.

#### `tools/html_to_pdf.py` (rewritten, backward compatible)
- New `--check` gives a detailed per-engine health report with
  actionable install hints.
- New `--engine {auto,weasyprint,playwright}` flag.
- Windows now prefers Playwright by default (avoids the GTK footgun).
- Structured `html_to_pdf()` Python API returns `(ok, engine_used)`.
- Exit codes documented: 0 success, 1 usage, 2 no engine, 3 crash.
- `atomic_write` is now a thin re-export from `tools.io_utils`.

#### Hooks (bash shims, gracefully degrade)
- **`hooks/truth-verification.sh`** and **`hooks/evidence-chain.sh`**
  rewritten as thin shims: try `tools/evidence_validator.py` first,
  fall back to the v1 grep heuristic if the v2 tools aren't installed.
  Real principle violations now **block** (exit 1) with actionable
  messages instead of only warning.

### Deps
- Added core: `pydantic>=2.5.0`, `pyyaml>=6.0.1`, `filelock>=3.13.0`.
- Optional / dev: `pytest`, `pytest-cov` (unchanged for legacy tests).

### Notes for existing users
- **Nothing breaks.** All v1 triggers, workflows, and file layouts
  continue to work exactly as before.
- New tools live under `tools/` and are invoked explicitly
  (`python -m tools.evidence_validator`, etc.). They will start being
  called automatically by v2 skills in P1/P2.
- Full migration path to v2 data layout: see
  [docs/v2/08-migration-v1-to-v2.md](docs/v2/08-migration-v1-to-v2.md).

---

## [1.3.0] - 2026-06-17

### Added

#### Sub-skills (新增)
- **resume-verify**: 代码溯源 + 知识验证（新增）
  - 项目框架扫描：自动识别技术栈、项目类型、构建工具、测试框架
  - 代码溯源分析：入口追踪、核心模块识别、业务流程追踪、架构模式识别
  - 生成 project-tmd.md：以开发者视角撰写完整项目经历（临时文件）
  - 知识验证提问：核心技术原理、架构设计理解、业务流程、问题排查、优化思路
  - 85% 阈值验证：通过后 project-tmd.md 重命名为 proj-<NNN>-<short>.md
  - 支持额外参考文件（设计文档、需求文档等）

#### Schema (更新)
- **state-schema**: 新增 `last_verify_at` 字段
  - 写入者：resume-verify
  - 每次代码验证后更新
- **project-schema**: 新增验证相关字段
  - `验证方式`: 代码溯源 / 对话深挖 / 简历导入
  - `验证状态`: ✅ 已验证 / ⏳ 待验证
  - `验证得分`: 可选，仅代码溯源验证时生成

### Changed

#### Design Decisions (决策)
- **模板渲染方案 B**：模板仅为布局参考，HTML 由 Claude 直接生成
  - 移除 Jinja2 渲染引擎依赖
  - 模板文件降级为"布局参考文档"
  - resume-build 直接基于模板风格生成 HTML

---

## [1.2.1] - 2026-06-14

### Fixed

#### Tools (修复)
- **resume_parser.py**: 工作经历提取全面修复
  - 支持 `**公司** | 职位` 格式（用户简历常用格式）
  - 支持英文公司名（Siemens, Google, Meta 等）
  - 支持从下一行提取日期（`*2023.07 - 至今*`）
  - 职责提取过滤掉 `**背景**`、`**行动**` 等子标题
  - 项目提取过滤掉工作经历标题（含公司名或 `|`）
  - 新增 `_extract_responsibilities()` 方法
- **keyword_matcher.py**: 关键词库从 40 个扩展到 150+ 个
  - 按领域分类：DevOps、Observability、Robotics、Industrial、AI/ML 等
  - 覆盖 PLC、SCADA、Modbus、AGV、RAG、LangChain 等工业/AI 关键词
  - 修复 Windows GBK 编码问题
- **html_to_pdf.py**: PDF 导出优化
  - Windows 上优先使用 playwright（不需要 GTK 系统库）
  - 新增 `--check` 命令检查可用引擎
  - 修复 Windows GBK 编码问题

#### Hooks (修复)
- **truth-verification.sh**: 移除 jq 依赖，改用 python 解析 JSON
- **evidence-chain.sh**: 移除 jq 依赖，改用 python 解析 JSON

#### Install (修复)
- **install.sh**: python3/pip3 fallback 到 python/pip
  - Windows 上 `python3` 指向 Store 占位符，自动降级到 `python`

---

## [1.2.0] - 2026-06-14

### Added

#### Documentation (新增)
- **docs/FIX-TASKS-v1.2.1.md**: 修复任务清单（来自本地测试）
  - 3 个 P0 阻断性问题（正则失败、关键词库窄、编码错误）
  - 3 个 P1 严重问题（Hook 依赖 jq、weasyprint GTK、逻辑不统一）
  - 2 个 P2 体验问题（install.sh python3、模板渲染）
  - 修复优先级排序和验证清单
- **docs/TECHNICAL-AUDIT-v1.2.0.md**: 全面技术审计文档
  - 架构层面 5 个实现断层分析（模板渲染、Hook 强制、工具链、测试、迁移）
  - 6 个需要真实测试验证的核心问题
  - 求职用户 10 大痛点 vs 系统覆盖度分析
  - 9 个建议新增功能（P0/P1/P2 三级优先级）
  - 依赖清单与技术债务清单
  - 风险矩阵
  - 真实用户测试方案（5 类用户画像 + 8 步测试流程）
  - 功能路线图（v1.3 → v1.4 → v1.5 → v2.0）
- **docs/LOCAL-TEST-GUIDE.md**: 本地测试指南
  - 10 个测试场景，每个场景有详细的步骤、观察指标、记录模板
  - 环境准备和依赖检查
  - 跨场景一致性检查
  - 问题反馈模板
  - 重点关注清单（按风险排序）

### Changed

#### resume-import (改进)
- **Phase 6 新增：模板策略询问**
  - 导入完成后询问用户是否保留原始模板
  - HTML/MD → 提取模板骨架，存入 `templates/imported/`
  - PDF → 降级为优化建议模式，用户手动修改原文件
  - 不保留 → 走系统模板或自定义模板流程
- 新增 `imported_template` 状态字段
- 输出结果区分三种场景（保留模板 HTML/MD、保留模板 PDF 降级、不保留）

#### resume-build (改进)
- Phase 1 优先检查 `imported_template` 字段
- 如果有导入模板，优先使用而非询问选择
- 模板选择列表新增"导入的模板"选项

#### state-schema (改进)
- 新增 `imported_template` 字段（string / null）
- 写入者：resume-import
- 读取者：resume-build

#### Sub-skills (新增)
- **resume-localize**: 中英文简历本地化（新增）
  - 文化适配转换（非逐句翻译）
  - 目标市场选择（有意向企业 → 企业分析；无意向企业 → 通用市场）
  - 内容改写（自我评价、工作经历、项目经历按目标市场习惯重写）
  - 格式适配（移除/添加照片、个人信息、调整日期格式）
  - 企业文化特征库（Google、Meta、Amazon、字节、阿里等）

#### Templates (新增)
- **tech-standard-en.html**: 英文技术岗模板（新增）
  - 无照片区域、无个人信息区域
  - 英文字体（Georgia、Helvetica）
  - 更大留白、LinkedIn/GitHub 链接
- **product-standard-en.html**: 英文产品岗模板（新增）

#### Shared References (新增)
- **localize-schema.md**: 本地化 schema（新增）
  - 目标市场枚举
  - 文化适配矩阵
  - 内容改写规则
  - 技能术语对照表
  - 企业文化特征库

#### Documentation (更新)
- 更新 TASK-OUTLINE.md，补充 resume-import 和 resume-localize

---

## [1.1.1] - 2026-06-14

### Fixed

#### Tools (修复)
- **resume_parser.py**: 简历解析器 bug 修复
  - 文件名：连字符 → 下划线（Python 无法导入带连字符的模块名）
  - 正则：education 的 `$` 缺少 `re.MULTILINE` 标志
  - 编码：Windows GBK 终端 emoji 输出报错
  - 提取质量：姓名、工作经历、项目经历、技能、教育背景、证书/荣誉全面优化

#### Tests (新增)
- **test_keyword_matcher.py**: 关键词匹配器测试（14 个测试）
- **test_html_to_pdf.py**: HTML 转 PDF 测试（5 个测试）
- 测试总数：26 个测试全部通过

---

## [1.1.0] - 2026-06-13

### Added

#### Sub-skills (新增)
- **resume-import**: 简历导入（新增）
  - 支持多种格式：pdf, doc, docx, md, html, txt
  - 解析简历内容，生成初步 Profile
  - 考察用户经历真实性
  - 分类处理：有效经历、马赛克项目、知识缺口

#### Tools (新增)
- **resume-parser.py**: 简历解析器（新增）
  - 支持 PDF, DOCX, DOC, MD, HTML, TXT 格式
  - 自动提取基本信息、工作经历、项目经历、技能清单

#### Examples (新增)
- **sample-resume.md**: 示例简历（新增）

#### Documentation (新增)
- **MEMORY.md**: 开发记忆文件（新增）
- **DEVELOPMENT.md**: 开发要求文档（新增）

### Changed

#### Core
- 更新路由表，添加 resume-import 触发词
- 更新文件清单，添加新增文件

---

## [1.0.0] - 2026-06-13

### Added

#### Core
- **SKILL.md**: 总协议 + 路由器
- **三条不可妥协原则**:
  - 真实性原则 (Truth First)
  - 针对性原则 (Tailored for You)
  - 证据链原则 (Evidence Chain)

#### Sub-skills (11)
- **resume-init**: 初始化
- **resume-mine**: 深挖经历
- **resume-profile**: 技能树管理
- **resume-jd**: JD 分析
- **resume-build**: 简历生成
- **resume-optimize**: 简历优化
- **resume-interview**: 面试准备
- **resume-learn**: 学习指导
- **resume-export**: 导出 PDF
- **resume-status**: 状态看板
- **resume-blind**: 盲评估

#### Shared References (8)
- **core-principles.md**: 核心原则
- **state-schema.md**: 状态文件 schema
- **project-schema.md**: 项目文档 schema
- **profile-schema.md**: 技能树 schema
- **jd-schema.md**: JD 分析 schema
- **resume-schema.md**: 简历 schema
- **interview-schema.md**: 面试 schema
- **learning-schema.md**: 学习 schema

#### Templates (2)
- **tech-standard.html**: 技术岗标准模板
- **tech-modern.html**: 技术岗现代模板

#### Hooks (2)
- **truth-verification**: 真实性校验
- **evidence-chain**: 证据链校验

#### Tools (2)
- **html-to-pdf.py**: HTML 转 PDF
- **keyword-matcher.py**: 关键词匹配

#### Examples (4)
- **sample-project.md**: 示例项目文档
- **sample-profile.md**: 示例技能树
- **sample-jd.md**: 示例 JD 分析
- **sample-interview.md**: 示例面试指导

### Features

#### Deep Mining (resume-mine)
- STAR 法则引导
- 量化成果要求
- 自动更新技能树

#### JD Analysis (resume-jd)
- 自动提取关键信息
- 技能匹配度分析
- 优化建议生成

#### Resume Building (resume-build)
- 针对性简历生成
- 多模板支持
- 版本管理

#### Interview Preparation (resume-interview)
- 自我介绍生成
- 项目深挖问题
- 技术问题准备
- 行为问题准备

#### Learning Guidance (resume-learn)
- 技能缺口分析
- 学习计划制定
- 学习资源推荐

#### Blind Evaluation (resume-blind)
- 独立评估简历质量
- 5 维度评分
- 改进建议

---

## [Unreleased]

### Planned
- 更多简历模板
- AI 辅助优化
- 面试模拟
- 学习进度跟踪
- 多语言支持

---

## Version History

| Version | Date | Description |
|---|---|---|
| 1.3.0 | 2026-06-17 | 代码溯源验证、模板渲染方案 B 决策 |
| 1.2.0 | 2026-06-14 | 中英文简历本地化、英文模板、解析器优化 |
| 1.1.1 | 2026-06-14 | 简历解析器 bug 修复、新增工具测试 |
| 1.1.0 | 2026-06-13 | 简历导入功能 |
| 1.0.0 | 2026-06-13 | 初始版本 |

---

## Migration Guide

### 从 0.x 到 1.0

1. 备份现有数据
2. 运行 `/resume-init` 重新初始化
3. 导入现有项目和简历

---

## Contributing

1. Fork 本仓库
2. 创建你的分支 (`git checkout -b feature/xxx`)
3. 提交你的改动 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 发起 Pull Request

---

## License

MIT License
