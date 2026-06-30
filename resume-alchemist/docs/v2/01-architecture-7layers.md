# 01 · 7 层架构总图

## 一、架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1 · Agent Adapter（任意 Agent + 任意 LLM 的接入层）                │
│                                                                          │
│  Claude Code   Cursor   Cline   ChatGPT   Gemini   Copilot   CLI/CI     │
│       │          │        │        │         │        │         │        │
│       └─────┬────┴────────┴────────┴─────────┴────────┴─────────┘        │
│             ↓                                                            │
│  ┌──────────────────────┐    ┌────────────────────────────────────┐    │
│  │ SKILL.md / .agent.md │    │ MCP Server  (mcp.resume.*  tools)  │    │
│  │ （Claude/Cursor 原生）│    │ stdio / SSE / HTTP transports      │    │
│  └──────────────────────┘    └────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 2 · Orchestrator（协议/路由/状态机）                                │
│                                                                          │
│  orchestrator.yaml （状态机定义）                                         │
│  ├── states: uninitialized / initialized / has_profile / has_jd / ...   │
│  ├── transitions（触发词 → 动作，与具体 agent 解耦）                       │
│  └── guards（前置条件，例如：build 前必须有 active_jd）                    │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 3 · Skill 包（方法论 prompt 集合，LLM-agnostic）                    │
│                                                                          │
│  intake   match   output   profile   review   status   coach            │
│  （这一层只产出 prompt 模板和工作流，不直接做事，由 Layer 4 工具执行）       │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 4 · Deterministic Tools（确定性工具，纯 Python）                     │
│                                                                          │
│  evidence_validator  match_scorer  renderer  parser  diff  exporter     │
│  migrate  keyword_extractor  i18n                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 5 · Knowledge Base（双轨制档案）                                    │
│                                                                          │
│  profile/   resumes/   learning/   .resume-state.json (派生)             │
│  事实存 data.yaml（程序消费） + 叙事存 narrative.md（人读/LLM 读）          │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 6 · Render & Export（多端输出）                                     │
│                                                                          │
│  HTML  PDF  Markdown  JSON Resume(标准)  DOCX  ATS-friendly plain text  │
│  （由 Jinja2 模板 + data.yaml 渲染，确定性、可复现）                       │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↑
                                  │ feedback signals
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 7 · Feedback Loop（投递结果 → 反向优化）                             │
│                                                                          │
│  outcomes.yaml  →  ROI 分析  →  weak-spot 识别  →  下一次迭代             │
│  traces/ （所有 LLM 调用脱敏后留底，可观测）                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## 二、依赖方向（重要：单向）

```
Agent Adapter  ──▶  Orchestrator  ──▶  Skill  ──▶  Tools  ──▶  KB  ──▶  Render
                                                                ↑
                                                                │
                                                       Feedback ┘
```

**关键纪律**：
- 上层依赖下层，**下层绝不反向依赖上层**
- Tools 层无状态、纯函数风格（输入 → 输出，副作用只写 KB）
- KB 层只存数据，不含业务逻辑
- Skill 层只生成 prompt + 编排 tool 调用，不直接操作 KB

## 三、各层职责详表

### Layer 1 · Agent Adapter

| Agent | 接入方式 | 资源文件 |
|---|---|---|
| Claude Code | 原生 SKILL.md | `~/.claude/skills/resume-alchemist/` |
| Cursor | `.cursorrules` + MCP | `mcp.json` 配置一个 server |
| Cline | MCP | 同上 |
| ChatGPT (web) | Custom GPT + Action(MCP via gateway) | 需要 MCP-over-HTTP gateway |
| Gemini CLI | MCP | 原生支持 |
| Copilot Chat | `.github/copilot-instructions.md` + MCP (when supported) | |
| 任意 CLI / CI | `resume` 命令 | pip 包 `resume-alchemist` |

**双层 SKILL.md** 结构（让方法论 prompt 可被任何 LLM 直接读懂）：

```markdown
---
# 上层：LLM-agnostic（任何 LLM 读都明白）
goal: 用 STAR 法则深挖一个项目经历
inputs: [项目名]
outputs: [profile/projects/<id>/data.yaml]
principles: [truth-first, evidence-chain]
---

# 普通自然语言的方法论描述（LLM 读这部分理解要做什么）

---
# 下层：agent-specific tool calls（不同 agent 各自取需要的部分）
tool_calls:
  claude_code:
    - read: profile/self-profile.md
    - run: resume.intake --mode dialog
  mcp:
    - tool: mcp.resume.intake
      args: {mode: "dialog"}
  cli:
    - cmd: resume intake --mode dialog
---
```

### Layer 2 · Orchestrator

把现在散在 [SKILL.md](../../SKILL.md) 路由表里的逻辑抽出来：

```yaml
# orchestrator.yaml
schema_version: 2.0

states:
  uninitialized:
    on:
      any: { target: init, action: route_to_init }

  initialized:
    guard: state.project_count >= 0
    on:
      "聊聊我的经历|deep dive|mine":  { action: intake.dialog }
      "导入简历|我有简历|import":      { action: intake.file }
      "这是我的项目代码|verify":       { action: intake.code }
      "分析这个 JD|analyze jd":      { action: match.jd, target: has_jd }
      "看看我的档案|show profile":    { action: profile.show }
      "状态|status":                  { action: status.dashboard }

  has_jd:
    guard: state.active_jd_id != null
    on:
      "生成简历|build resume":   { action: output.resume, requires: [intake] }
      "准备面试|interview":      { action: output.interview }
      "学什么|learn":            { action: output.learning_plan }
      "我投了 / 收到面试 / 拒信": { action: feedback.track }

global_intents:
  show_me:
    pattern: "(?:show me|show|看看)\\s+(profile|skills|resume|jd|outcomes)"
    action: render.preview
  diff:
    pattern: "diff|对比"
    action: render.diff
```

**好处**：
- 路由逻辑可单元测试
- 跨 agent 共用一份配置
- 改路由不用动十几个 SKILL.md
- 新加 agent 只需写"如何把 agent 的输入 → orchestrator 的 event"

### Layer 3 · Skill 包

13 → 7 重构，详见 [05-skills-redesign.md](05-skills-redesign.md)。这里只列对照表：

| v2 Skill | 合并自 v1 | 类型 |
|---|---|---|
| `intake` | mine + import + verify | 动词·录入 |
| `match` | jd | 动词·匹配 |
| `output` | build + optimize + interview + learn + export + localize | 动词·产出 |
| `profile` | profile | 引擎·档案 |
| `review` | blind | 引擎·盲评 |
| `status` | status + (新)track | 引擎·看板 |
| `coach` | （新） | 引擎·角色化教练 |

`coach` 是关键新增：根据 `target_role` 动态注入不同人格（技术教练 / PM 教练 / 设计教练），决定 `intake` 怎么问、`match` 怎么算权重、`review` 怎么打分。

### Layer 4 · Deterministic Tools

完整 spec 见 [03-tools-layer-spec.md](03-tools-layer-spec.md)，这里给清单：

| 工具 | 输入 | 输出 | 替代 v1 的什么 |
|---|---|---|---|
| `evidence_validator` | data.yaml + resume.yaml | 报告 (含违规项) | hooks/*.sh |
| `match_scorer` | jd.yaml + profile.yaml | 匹配度 JSON | keyword_matcher.py |
| `renderer` | data.yaml + template | HTML / MD / DOCX | LLM 直接生成 HTML |
| `parser` | resume.pdf/docx/md | data.yaml | resume_parser.py |
| `diff` | data.yaml v1 vs v2 | unified diff + 解释 | （新增） |
| `exporter` | HTML | PDF | html_to_pdf.py |
| `keyword_extractor` | JD 文本 | keywords + 权重 | keyword_matcher.py 的一部分 |
| `migrate` | v1 .resume-state.json | v2 schema | （新增） |
| `i18n` | data.yaml + target locale | 本地化后的 data.yaml | resume-localize 内嵌逻辑 |

### Layer 5 · Knowledge Base

完整 spec 见 [02-data-layer-spec.md](02-data-layer-spec.md)。核心规则：

```
profile/
  projects/
    proj-001-xxx/
      data.yaml         ← 单一事实来源
      narrative.md      ← 由 data.yaml + 模板渲染（可重生成）
      evidence/         ← 真凭实据
        commit-abc.md
        screenshot.png
  self-profile/
    data.yaml
    narrative.md
  work-history/
    company-001/
      data.yaml
      narrative.md

resumes/
  jd-001-xxx/
    jd.yaml             ← JD 解析结果
    jd-analysis.md      ← 渲染产物
    resume-v1.yaml      ← 简历内容（不是 HTML，是数据）
    resume-v1.html      ← 渲染产物
    resume-v1.pdf       ← 导出产物
    interview-guide.yaml
    outcomes.yaml       ← v2 新增：投递结果
```

`.resume-state.json` 在 v2 中**降级为派生 cache**，不再是事实来源。每次启动用 `tools/state_builder.py` 从 KB 重建。

### Layer 6 · Render & Export

```python
# 调用示例（伪代码）
from resume_alchemist.tools import renderer

renderer.render(
    data="resumes/jd-001/resume-v1.yaml",
    template="templates/official/tech-modern.html.j2",
    output="resumes/jd-001/resume-v1.html",
)
```

支持的输出格式：

| 格式 | 用途 |
|---|---|
| HTML | 在线分享 / 浏览器查看 |
| PDF | 投递 |
| Markdown | GitHub 个人主页 |
| JSON Resume | [jsonresume.org](https://jsonresume.org/) 标准，可被其他工具消费 |
| DOCX | 部分企业 HR 系统要求 |
| Plain Text | ATS 友好版本（剥离样式） |

### Layer 7 · Feedback Loop

完整 spec 见 [06-feedback-loop.md](06-feedback-loop.md)。核心环节：

```
用户投了简历
  ↓
resume track  ──→ outcomes.yaml.events[] 追加 event
  ↓
ROI 分析 (tools/roi_analyzer.py)
  ↓
更新 .resume-state.json (派生统计)
  ↓
下次 resume status 显示真·dashboard
  ↓
下次 resume build / interview / learn 时，coach 读这些信号给个性化建议
```

## 四、跨层契约（接口稳定性约定）

| 契约 | 稳定性 | 说明 |
|---|---|---|
| `data.yaml` schemas | 🔒 强稳定 | schema_version 跟随 SemVer，破坏性改动必走 migration |
| Tools 的 CLI/Python API | 🔒 强稳定 | 工具之间互相调用、MCP 暴露都靠它 |
| Orchestrator events | 🟡 中稳定 | 加新 event OK，删 event 走 deprecation |
| Skill prompt 文本 | 🟢 弱稳定 | 鼓励持续打磨 |
| Renderer 模板 | 🟢 弱稳定 | 用户可以 fork 模板自定义 |

## 五、为什么是 7 层而不是 3 层

被问过："这是不是过度设计？"

回答：每一层都有**单一明确职责**，且**少了任何一层都会回到 v1 的问题**：

| 砍掉 | 后果 |
|---|---|
| 砍 Agent Adapter | 退回 Claude Code 专属，违反"跨 agent"目标 |
| 砍 Orchestrator | 路由散到各 SKILL.md，无法跨 agent 共用、无法单测 |
| 砍 Tools | 让 LLM 干渲染/校验/匹配，回到 v1 的不确定性 |
| 砍 KB 双轨制 | 回到 markdown-only，证据链工程化无从谈起 |
| 砍 Render | 让 LLM 拼 HTML，样式漂移 |
| 砍 Feedback | 系统永远开环，无法学习 |

7 层不是为了显得复杂，是因为**少一层都不行**。但每层的接口要薄、要严，所以总代码量不会爆炸。

下一章：[02-data-layer-spec.md](02-data-layer-spec.md)
