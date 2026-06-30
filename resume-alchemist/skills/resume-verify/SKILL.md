---
name: resume-verify
description: 代码溯源验证：分析项目源码，以开发者视角还原完整项目经历，通过提问验证用户对项目的理解深度。触发词："验证项目"/"代码溯源"/"这是我的项目代码"/"分析项目代码"。
argument-hint: <project-path> [--files <extra-files>]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /resume-verify — 代码溯源 + 知识验证

从代码出发，验证你是否真正参与过这个项目。

## 为什么需要代码溯源？

简历炼金术士有三条不可妥协原则，其中**真实性原则**和**证据链原则**要求：
- 简历内容必须基于真实经历
- 每项技能必须有项目支撑

传统的 `/resume-mine` 依赖用户口述，`/resume-import` 依赖简历文本——两者都无法从代码层面验证。

**resume-verify 的定位**：
- 以**代码为起点**，逆向还原开发者视角的完整项目经历
- 通过**知识验证**确认用户对项目的理解深度
- 通过验证后，自动生成符合 project-schema 的正式项目文档

## Overview

```
[用户：验证项目 / 这是我的项目代码]
  ↓
[Phase 0: 检查前置条件]
  ↓
[Phase 1: 项目框架扫描]
  ↓
[Phase 2: 代码溯源分析]
  ↓
[Phase 3: 生成 project-tmd.md（临时文件）]
  ↓
[Phase 4: 知识验证提问]
  ↓
[Phase 5: 评分 + 正式命名]
  ├─ ≥85% → project-tmd.md → proj-<NNN>-<short>.md
  ├─ 60-84% → 保留 project-tmd.md + 学习建议
  └─ <60% → 保留 project-tmd.md + 引导 /resume-learn
  ↓
[Phase 6: 更新状态 + 输出结果]
```

## Constants

- **PASS_THRESHOLD = 0.85** — 验证通过阈值（85%）
- **PARTIAL_THRESHOLD = 0.60** — 部分通过阈值（60%）
- **SCAN_DEPTH = 3** — 目录扫描深度
- **MAX_QUESTIONS = 15** — 最大验证题目数
- **MIN_QUESTIONS = 8** — 最少验证题目数

## Inputs

| 必填 | 来源 | 说明 |
|---|---|---|
| `<project-path>` | 用户提供 | 项目根目录路径 |
| `--files <extra-files>` | 用户提供（可选） | 额外参考文件（设计文档、需求文档等） |
| `.resume-state.json` | 项目根 | 前置条件检查 |

> **重要**：resume-verify 是**独立封闭**的 skill。只分析用户本次给出的代码项目，**不读取** `profile/self-profile.md`、`profile/projects/*.md` 或任何历史项目文档。不是所有项目都有代码，不是所有用户都是程序员——历史项目通过 `/resume-mine` 或 `/resume-import` 创建，与本 skill 无关。

## Workflow

### Phase 0: 检查前置条件

1. 读 `.resume-state.json` → 不存在则路由到 `/resume-init`
2. 检查 `<project-path>` 是否存在且为目录
3. 检查目录是否包含可分析的代码文件
4. **不读取** `profile/self-profile.md` 或 `profile/projects/*.md` — 本 skill 只关注用户本次给出的代码

**前置条件不满足时的处理**：
- 路径不存在 → "路径不存在，请检查后重试"
- 路径是文件而非目录 → "请提供项目根目录路径，而非单个文件"
- 目录为空或无可分析代码 → "目录中未发现可分析的代码文件。如果你的项目没有代码（如文档、设计、运营类项目），请使用 `/resume-mine` 通过对话深挖经历"

### Phase 1: 项目框架扫描

扫描项目目录，识别技术栈和项目结构。

#### 1.1 技术栈识别

| 检测文件 | 推断结果 |
|---|---|
| `package.json` | Node.js 项目，读取 dependencies/devDependencies |
| `requirements.txt` / `pyproject.toml` / `setup.py` | Python 项目，读取依赖 |
| `go.mod` | Go 项目，读取 require |
| `pom.xml` / `build.gradle` | Java 项目，读取依赖 |
| `Cargo.toml` | Rust 项目 |
| `Gemfile` | Ruby 项目 |
| `composer.json` | PHP 项目 |
| `*.csproj` / `*.sln` | C#/.NET 项目 |

#### 1.2 项目类型识别

| 特征 | 推断 |
|---|---|
| 有 `app.py` / `main.py` + Flask/Django/FastAPI | Web 后端 |
| 有 `src/index.ts` + React/Vue/Angular | Web 前端 |
| 有 `manage.py` + `settings.py` | Django 项目 |
| 有 `Dockerfile` + `docker-compose.yml` | 容器化项目 |
| 有 `cmd/` 目录 + `main.go` | Go CLI/服务 |
| 有 `__main__.py` | Python CLI |
| 有 `lib/` 或 `src/` 且无入口文件 | 库/SDK |
| 有多个子目录各含独立 `main` / `app` | 微服务/monorepo |

#### 1.3 构建与部署识别

| 检测文件 | 推断 |
|---|---|
| `Makefile` | Make 构建 |
| `webpack.config.*` / `vite.config.*` | 前端构建 |
| `Dockerfile` | Docker 构建 |
| `.github/workflows/*.yml` | GitHub Actions CI |
| `.gitlab-ci.yml` | GitLab CI |
| `Jenkinsfile` | Jenkins CI |
| `k8s/` / `deploy/` | K8s 部署 |

#### 1.4 测试框架识别

| 检测文件 | 推断 |
|---|---|
| `jest.config.*` / `*.test.ts` | Jest |
| `pytest.ini` / `test_*.py` / `*_test.py` | pytest |
| `*_test.go` | Go testing |
| `*.spec.ts` / `*.spec.js` | Jasmine/Mocha |
| `src/test/` | Java JUnit |

#### 1.5 输出扫描摘要

```
📊 项目扫描结果：

- 项目类型：Web 后端服务
- 主要语言：Python 3.11
- 核心框架：FastAPI 0.104 + SQLAlchemy 2.0
- 数据库：PostgreSQL（检测到 alembic 迁移）
- 构建工具：Docker + docker-compose
- 测试框架：pytest（12 个测试文件）
- CI/CD：GitHub Actions
- 项目规模：~85 个 Python 文件，~6200 行代码

正在进入代码溯源分析...
```

### Phase 2: 代码溯源分析

深入分析代码，以开发者视角理解项目。

#### 2.1 入口文件追踪

1. 找到项目入口（main.py / app.py / index.ts / cmd/main.go 等）
2. 从入口开始追踪调用链
3. 识别核心初始化流程
4. 绘制调用链路图

#### 2.2 核心模块识别

**方法**：
- 统计每个模块被 import/require 的次数
- 按被引用频率排序，Top 5-10 为核心模块
- 分析每个核心模块的职责

**输出**：
```
核心模块（按引用频率排序）：
1. models/user.py (被引用 12 次) — 用户数据模型
2. services/auth.py (被引用 9 次) — 认证服务
3. core/database.py (被引用 8 次) — 数据库连接
4. api/routes.py (被引用 7 次) — API 路由定义
5. utils/cache.py (被引用 5 次) — 缓存工具
```

#### 2.3 关键业务流程追踪

**方法**：
- 从 API 路由（或 CLI 命令）出发
- 追踪：路由 → handler → service → repository → database
- 识别数据流向和业务逻辑

**输出**：
```
关键业务流程：
1. 用户注册：POST /api/register → auth.register() → user.create() → db.insert()
2. 订单创建：POST /api/orders → order.create() → inventory.check() → payment.process()
3. 数据导出：GET /api/export → export.generate() → query.build() → file.write()
```

#### 2.4 架构模式识别

| 模式 | 特征 |
|---|---|
| MVC | models/ + views/ + controllers/ |
| 分层架构 | api/ + service/ + repository/ + model/ |
| 事件驱动 | events/ + handlers/ + message queue |
| 微服务 | 多个独立服务目录，各自有入口 |
| CQRS | commands/ + queries/ |
| 六边形架构 | ports/ + adapters/ |

#### 2.5 第三方依赖分析

**分类**：
- **核心依赖**：项目运行必需（框架、数据库驱动）
- **业务依赖**：实现特定功能（支付 SDK、短信服务）
- **开发依赖**：开发/测试工具（linter、测试框架）

**分析维度**：
- 为什么选这个库？（从代码使用方式推断）
- 有没有替代方案？
- 版本是否过时？

#### 2.6 Git 历史分析（如有 .git 目录）

```bash
# 贡献者统计
git shortlog -sn --no-merges

# 提交频率
git log --format="%ai" | cut -d' ' -f1 | sort | uniq -c

# 关键变更（大 commit）
git log --stat --diff-filter=M --summary | head -100

# 文件变更热度
git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -20
```

#### 2.7 代码亮点识别

- **设计模式使用**：单例、工厂、观察者、策略模式等
- **性能优化**：缓存策略、异步处理、批量操作
- **安全措施**：输入校验、SQL 注入防护、XSS 防护
- **错误处理**：全局异常处理、重试机制、降级策略
- **可扩展性**：插件机制、配置化、抽象层

### Phase 3: 生成 project-tmd.md（临时文件）

基于 Phase 1-2 的分析结果，以开发者视角撰写完整的项目经历文档。

**文件位置**：`profile/projects/project-tmd.md`（临时文件名）

**文档结构**：

```markdown
# [项目名称] — 代码溯源报告

**溯源时间**: YYYY-MM-DD
**项目路径**: <path>
**分析方式**: 代码溯源
**验证状态**: ⏳ 待验证

---

## 一、项目概览

- **项目类型**：Web 应用 / CLI 工具 / 微服务 / ...
- **主要语言**：Python 3.11 / TypeScript 5.x / ...
- **核心框架**：FastAPI 0.104 / React 18 / ...
- **项目规模**：~XX 文件，~XX 行代码
- **项目周期**：（从 git 历史推断，如有）

## 二、技术架构

### 2.1 整体架构

（架构模式描述 + 架构图）

### 2.2 目录结构

（树形图 + 各目录职责说明）

### 2.3 核心依赖

| 依赖 | 版本 | 用途 | 重要度 |
|---|---|---|---|
| ... | ... | ... | 核心/业务/开发 |

### 2.4 数据流

（关键数据的流向描述）

## 三、项目生命周期

> 根据代码分析结果，合理选择以下阶段（不要求全部包含）：

### 3.1 需求分析（从代码推断）

（从功能模块、API 端点、数据模型推断业务需求）

### 3.2 技术设计

（从架构、设计模式、模块划分推断设计决策）

### 3.3 开发实现

#### 核心模块 1：[模块名]
- **职责**：...
- **关键代码**：`path/to/file.py:L42-L80`
- **设计模式**：...
- **技术亮点**：...

#### 核心模块 2：[模块名]
...

### 3.4 测试策略（如有测试代码）

- 测试框架：...
- 测试文件数：...
- 测试类型：单元 / 集成 / E2E

### 3.5 部署与运维（如有部署配置）

- 容器化：Docker / K8s
- CI/CD：GitHub Actions / GitLab CI
- 环境配置：...

## 四、代码亮点与技术难点

### 4.1 设计亮点
- ...

### 4.2 技术难点
- ...

### 4.3 可优化点
- ...

## 五、面试准备素材

### 5.1 项目介绍（1 分钟版）

（基于代码分析生成的项目介绍模板）

### 5.2 技术深挖方向

- 为什么选择 XX 框架？
- XX 模块的并发处理方案？
- 数据库查询优化策略？

### 5.3 常见追问

- Q: 如果并发量增加 10 倍，怎么优化？
- Q: 这个系统的单点故障在哪？
- Q: 如果重新设计，你会改什么？
```

**关键规则**：
- 所有内容必须**基于代码证据**，不能凭空推断
- 不确定的部分标注"（推断）"或"（待确认）"
- 代码引用使用 `file_path:line_number` 格式
- 使用原子写：.tmp → rename

### Phase 4: 知识验证提问

基于代码分析结果，向用户提问验证其对项目的理解。

#### 4.1 验证维度与权重

| 维度 | 权重 | 题目数 | 说明 |
|---|---|---|---|
| 核心技术原理 | 30% | 3-5 题 | 框架/语言核心概念 |
| 架构设计理解 | 25% | 2-3 题 | 为什么这样设计 |
| 业务流程理解 | 20% | 2-3 题 | 关键链路怎么走 |
| 问题排查能力 | 15% | 2-3 题 | 出了 bug 怎么查 |
| 优化改进思路 | 10% | 1-2 题 | 如果重新设计 |

#### 4.2 提问策略

> **所有问题必须来源于本次代码分析**，不读取用户的简历、技能树或历史项目。

**来源 1：代码中发现的技术点**
```
代码中使用了 Redis 做缓存（utils/cache.py），
能聊聊为什么选 Redis 而不是 Memcached 吗？
```

**来源 2：代码中使用但可能不理解原理的技术**
```
代码中大量使用了 async/await（services/async_worker.py），
能聊聊 Python 的事件循环机制吗？
```
> 基于代码本身推断用户可能接触但未必深入理解的技术，不依赖任何外部信息。

**来源 3：面试常见疑点**
```
这个项目的数据库查询用了 N+1 查询模式（models/），面试官可能会问：
"这里有什么性能问题？你会怎么优化？"
```

**来源 4：架构设计决策**
```
项目用了分层架构（api/ → service/ → repository/），
为什么不用更简单的直接调用？分层的好处是什么？
```

#### 4.3 评分标准

每题 0-10 分：

| 分数 | 标准 |
|---|---|
| 9-10 | 回答准确、有深度、能举一反三 |
| 7-8 | 回答正确，有一定深度 |
| 5-6 | 回答基本正确，但缺少细节 |
| 3-4 | 回答模糊或部分错误 |
| 1-2 | 回答错误或完全不了解 |
| 0 | 拒绝回答或完全跑题 |

#### 4.4 提问流程

1. 先说明验证规则："接下来我会根据代码分析问 XX 个问题，验证你对项目的理解。如实回答即可，不了解的可以说'不了解'。"
2. 逐题提问，记录用户回答
3. 每题回答后简要反馈（不透露标准答案）
4. 全部完成后计算总分

**关键规则**：
- 不要像审问，语气应该是**交流探讨**
- 允许用户说"不了解"，但会影响该维度得分
- 不要一次问太多问题（MIN_QUESTIONS ~ MAX_QUESTIONS）
- 根据用户回答质量动态调整后续问题难度

### Phase 5: 评分 + 正式命名

#### 5.1 评分计算

```
加权总分 = Σ(维度平均分 × 维度权重) × 10
结果保留整数
```

#### 5.2 验证结果处理

**🟢 高参与度（≥85%）— 通过**

操作：
1. 读取 `profile/projects/` 下已有的 `proj-*.md` 文件
2. 计算下一个编号：`max(已有编号) + 1`
3. 从项目名称中提取短名（3-8 字）
4. 将 `project-tmd.md` 转换为 `proj-<NNN>-<short>.md`：
   - 在文件头部添加元数据（项目 ID、验证状态、验证时间、验证得分）
   - 将"验证状态: ⏳ 待验证"改为"✅ 已验证"
   - 按 project-schema.md 格式调整结构
5. 原子写：.tmp → rename
6. 删除 `project-tmd.md`（如果 rename 不是原子操作）

**🟡 中参与度（60-84%）— 部分通过**

操作：
1. 保留 `project-tmd.md`
2. 在文件头部追加验证结果摘要
3. 生成学习建议（针对得分低的维度）
4. 建议用户补充知识后重新验证

输出：
```
📊 验证结果：🟡 中参与度（72/100）

各维度得分：
- 核心技术原理：8/10 ✅
- 架构设计理解：7/10 ✅
- 业务流程理解：6/10 ⚠️
- 问题排查能力：5/10 ⚠️
- 优化改进思路：7/10 ✅

📁 文件：profile/projects/project-tmd.md（保留）

💡 建议：
- 补充业务流程的理解（特别是 XX 模块的数据流）
- 练习问题排查场景（"XX 报错了怎么查？"）
- 准备好后可以说"重新验证项目"
```

**🔴 低参与度（<60%）— 未通过**

操作：
1. 保留 `project-tmd.md` 作为学习参考
2. 引导用户通过 `/resume-learn` 补充知识
3. 或引导用户通过 `/resume-mine` 重新深挖

输出：
```
📊 验证结果：🔴 低参与度（45/100）

这个项目的代码分析已完成，但验证未通过。
可能的原因：
- 你在这个项目中参与度较低
- 项目技术栈你不熟悉
- 项目代码是他人编写的

📁 代码溯源报告：profile/projects/project-tmd.md（学习参考）

💡 建议：
a) 如果你确实参与了这个项目 → 重新验证（补充知识后）
b) 如果参与度不高 → 通过 /resume-learn 学习相关技术
c) 如果想重新深挖 → 通过 /resume-mine 从对话开始
```

### Phase 6: 更新状态 + 输出结果

#### 6.1 更新 self-profile.md（仅验证通过时）

> 此步骤只在验证通过（≥85%）时执行。中/低参与度不更新 profile。

1. 读取 `profile/self-profile.md`
2. 根据**本次代码分析结果**更新技能树：
   - 通过验证的技能 → 更新证据强度为 🟢 强
   - 未通过验证的技能 → 保持或降级
3. 更新项目经历列表（添加本次验证的项目）
4. 原子写：.tmp → rename

**注意**：更新时只添加/修改本次验证的项目信息，不修改其他项目。

#### 6.2 更新 .resume-state.json

```python
state["project_count"] += 1  # 如果验证通过
state["last_verify_at"] = "<当前时间 ISO 8601>"
```

#### 6.3 输出结果

```
✅ 代码溯源验证完成

📊 验证结果：🟢 高参与度（92/100）

📁 文件：
- profile/projects/proj-003-电商系统.md（正式项目文档）
- profile/self-profile.md（已更新）

🔑 技能更新：
- Python: 精通 🟢 强（代码溯源验证）
- FastAPI: 熟练 🟢 强（代码溯源验证）
- Redis: 熟练 🟡 弱（验证未完全通过）

📋 下一步：
- 分析 JD？→ "分析这个 JD [粘贴 JD]"
- 继续验证其他项目？→ "验证项目 <路径>"
- 查看技能树？→ "看看我的技能树"
- 生成简历？→ "针对这个 JD 优化简历"
```

## Key Rules

1. **代码为证**——所有分析必须基于代码证据，不能凭空推断
2. **如实标注**——不确定的部分标注"（推断）"或"（待确认）"
3. **不造假经历**——代码分析结果只是素材，不能帮用户编造没做过的工作
4. **验证公平**——问题从代码中来，评分标准一致，不因用户身份不同
5. **尊重用户**——验证未通过时不指责，给出建设性建议
6. **原子写**——所有文件更新使用 .tmp → rename
7. **project-tmd.md 是临时文件**——验证通过后必须重命名为 proj-<NNN>-<short>.md
8. **封闭分析**——只分析用户本次给出的代码项目，**不读取** `profile/projects/*.md` 或 `profile/self-profile.md` 来交叉验证。不是所有项目都有代码，历史项目通过 `/resume-mine` 或 `/resume-import` 创建，与本 skill 无关

## Refusals

- 「帮我编一段我没做过的项目经历」 → 拒绝。简历炼金术士只炼真金
- 「跳过验证，直接生成项目文档」 → 拒绝。验证是确保面试成功的关键
- 「这个项目不是我做的，帮我分析一下」 → 可以分析代码，但不会标记为"已验证"
- 「把验证分数改高一点」 → 拒绝。评分标准一致，不可篡改
- 「project-tmd.md 就是最终文件，不需要重命名」 → 拒绝。必须按 proj-<NNN>-<short>.md 规范命名

## Integration

- 上游：用户提供项目路径
- 上游：`/resume-init` 创建初始档案
- 下游：`/resume-profile` 更新技能树（Phase 6 自动执行）
- 下游：`/resume-jd` 分析 JD 时会读取验证后的 proj-*.md
- 下游：`/resume-build` 生成简历时会读取验证后的 proj-*.md
- 下游：`/resume-interview` 面试准备时会读取验证后的 proj-*.md
- 下游：`/resume-learn` 验证未通过时引导学习
- 更新：`.resume-state.json` 的 `project_count`、`last_verify_at`
