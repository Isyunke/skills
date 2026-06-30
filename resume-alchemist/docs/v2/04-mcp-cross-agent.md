# 04 · 跨 Agent 接入层（MCP / CLI / 原生 SKILL.md）

> v1 最大的问题：只能在 Claude Code 用。
> v2 的目标：**任何 agent + 任何 LLM** 都能用同一套核心能力。
> 解决方案：MCP Server（一等公民） + CLI（兜底） + 双层 SKILL.md（原生体验）。

---

## 一、接入方式总览

| Agent / 平台 | 接入方式 | 体验等级 | 维护成本 |
|---|---|---|---|
| Claude Code | 原生 SKILL.md + MCP（双通道） | ⭐⭐⭐⭐⭐ | 中（v1 已有） |
| Cursor / Cline | MCP（`mcp.json`） | ⭐⭐⭐⭐⭐ | 低 |
| Claude Desktop | MCP（`claude_desktop_config.json`） | ⭐⭐⭐⭐⭐ | 低 |
| Gemini CLI | MCP（原生支持） | ⭐⭐⭐⭐ | 低 |
| Continue.dev | MCP | ⭐⭐⭐⭐ | 低 |
| Copilot Chat / VS Code Agent | MCP（VS Code 1.96+） | ⭐⭐⭐⭐ | 低 |
| ChatGPT (web) | Custom GPT + Action（需 MCP→HTTP gateway） | ⭐⭐⭐ | 中 |
| 任意 LLM（直接 prompt） | 把双层 SKILL.md 喂给 LLM | ⭐⭐ | 零 |
| CI / 自动化脚本 | `resume` CLI | ⭐⭐⭐⭐⭐ | 零 |

**核心策略**：MCP 是头等输出；其他都是它的薄包装。

---

## 二、MCP Server 设计

### 2.1 选型

| 选项 | 决策 |
|---|---|
| MCP SDK | **Python 官方 SDK**（`mcp` 包），与 tools/ 同语言 |
| Transport | 全部支持：`stdio`（本地）/ `SSE`（远程）/ `streamable-http` |
| 框架 | `FastMCP`（官方推荐，最简洁） |
| 部署 | 用户本地跑（不需要云服务） |

### 2.2 启动方式

```bash
# 本地（agent 通过 stdio 直接 spawn）
resume serve --transport stdio

# 长驻服务（多 agent 共用）
resume serve --transport sse --port 7777

# 远程访问（需要授权）
resume serve --transport http --port 7777 --auth-token $TOKEN
```

### 2.3 Agent 端配置示例

**Claude Desktop / Claude Code** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "resume-alchemist": {
      "command": "resume",
      "args": ["serve", "--transport", "stdio"],
      "env": {
        "RESUME_PROJECT_ROOT": "/path/to/user/resume-project"
      }
    }
  }
}
```

**Cursor / Cline / Continue** (`mcp.json` 通用):

```json
{
  "mcpServers": {
    "resume-alchemist": {
      "command": "resume",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

**Gemini CLI**: 同上格式，写入 `~/.config/gemini-cli/mcp.json`。

**VS Code 1.96+ Agent Mode**:

```json
// .vscode/mcp.json
{
  "servers": {
    "resume-alchemist": {
      "type": "stdio",
      "command": "resume",
      "args": ["serve"]
    }
  }
}
```

### 2.4 暴露的 MCP Tools

按 [Layer 3 Skill 包](01-architecture-7layers.md#layer-3--skill-包) 的 7 大动词暴露：

| MCP Tool 名 | 输入 schema | 用途 | 对应 v2 Skill |
|---|---|---|---|
| `resume.init` | `{role, industry, experience_level}` | 初始化项目 | init 阶段 |
| `resume.intake.dialog` | `{topic?: string}` | 启动对话式录入（返回引导 prompt） | intake |
| `resume.intake.file` | `{file_path: string}` | 解析简历文件入 KB | intake |
| `resume.intake.code` | `{project_path: string}` | 代码溯源验证 | intake |
| `resume.intake.confirm` | `{draft_id, edits[]}` | 用户确认草稿，落盘 | intake |
| `resume.match.jd` | `{jd_text \| jd_url}` | JD 解析 + 匹配度 | match |
| `resume.output.build` | `{jd_id, template?, locale?}` | 生成简历 | output |
| `resume.output.optimize` | `{resume_id, focus[]?}` | 优化简历 | output |
| `resume.output.interview` | `{jd_id}` | 生成面试指南 | output |
| `resume.output.learning_plan` | `{skill_gap[]}` | 生成学习计划 | output |
| `resume.output.export` | `{resume_id, format: pdf\|docx\|jsonresume}` | 导出 | output |
| `resume.profile.show` | `{section?}` | 渲染档案预览 | profile |
| `resume.review.blind` | `{resume_id, jd_id}` | 盲评估（隔离 context） | review |
| `resume.status` | `{verbose?}` | dashboard 数据 | status |
| `resume.diff` | `{path_a, path_b}` | 语义 diff | tools |
| `resume.track` | `{jd_id, event}` | 记录投递结果 | feedback |
| `resume.validate` | `{strict?}` | 跑 evidence_validator | tools |
| `resume.migrate` | `{from_version, to_version, dry_run?}` | v1→v2 迁移 | tools |

每个 tool 都用 Pydantic 严格定义 input/output schema，MCP 自动生成 JSON Schema 暴露给 agent。

### 2.5 Tool 实现示例

```python
# resume_alchemist/mcp_server/tools/intake.py
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("resume-alchemist")

class IntakeFileInput(BaseModel):
    file_path: str = Field(..., description="简历文件路径，支持 PDF/DOCX/MD")
    auto_confirm: bool = Field(False, description="是否跳过用户确认（不推荐）")

class IntakeFileOutput(BaseModel):
    draft_id: str
    parsed_summary: dict
    needs_confirmation: list[str]   # 字段哪些不确定
    next_prompt: str                # 给 LLM 的引导 prompt

@mcp.tool()
def intake_file(input: IntakeFileInput) -> IntakeFileOutput:
    """从文件导入简历到 KB。返回草稿，需 confirm 后才落盘。"""
    from resume_alchemist.tools import parser
    result = parser.parse(input.file_path)
    return IntakeFileOutput(
        draft_id=result.draft_id,
        parsed_summary=result.summary,
        needs_confirmation=result.uncertain_fields,
        next_prompt=PROMPTS.confirm_intake.format(**result.summary),
    )
```

### 2.6 MCP Resources

除了 tools，还暴露 resources（agent 可"读取"的虚拟文件）：

| Resource URI | 内容 |
|---|---|
| `resume://state` | 当前 .resume-state.json |
| `resume://profile` | 渲染后的档案预览 |
| `resume://skills` | 技能树预览 |
| `resume://jd/{jd_id}` | JD 分析报告 |
| `resume://resume/{resume_id}` | 简历预览 |
| `resume://outcomes/dashboard` | ROI dashboard |

agent 可主动读，不必每次都调 tool。

### 2.7 MCP Prompts

暴露**预设 prompt 模板**给 agent，用户在 agent 中可直接"召唤"：

```python
@mcp.prompt()
def deep_dive_project(project_id: str | None = None) -> str:
    """STAR 法则深挖项目经历"""
    return PROMPT_LIBRARY["intake_dialog"].format(project_id=project_id)

@mcp.prompt()
def prepare_for_interview(jd_id: str) -> str:
    """根据 JD 准备面试"""
    ...
```

用户在 Claude Desktop 里点击 / 输入 `@resume-alchemist deep-dive-project`，就能加载这些 prompt。

---

## 三、CLI（兜底通道）

### 3.1 设计原则

- 任何能在 agent 里做的事，CLI 都能做
- CI / 自动化脚本可用
- 不依赖 LLM 的动作（render / export / validate / migrate）可纯本地跑

### 3.2 CLI 命令树

```
resume
├── init                # 等价 resume.init MCP tool
├── intake
│   ├── dialog          # 输出引导 prompt（让外部 LLM 接力）
│   ├── file FILE
│   ├── code PATH
│   └── confirm DRAFT_ID
├── match JD_FILE
├── build               # 生成简历
├── optimize RESUME_ID
├── interview JD_ID
├── learn SKILL
├── export
│   ├── pdf RESUME_ID
│   ├── docx RESUME_ID
│   └── jsonresume RESUME_ID
├── profile
│   ├── show
│   ├── skills
│   └── projects
├── review RESUME_ID JD_ID
├── status              # dashboard
├── diff PATH_A PATH_B
├── track JD_ID EVENT_TYPE [...]
├── validate
├── render
├── migrate             # v1 → v2
└── serve               # MCP server
    ├── --transport stdio
    ├── --transport sse
    └── --transport http
```

### 3.3 CLI ↔ MCP 等价性

| CLI | MCP |
|---|---|
| `resume intake file CV.pdf` | `mcp.resume.intake.file({file_path: "CV.pdf"})` |
| `resume build` | `mcp.resume.output.build({jd_id})` |
| `resume status` | `mcp.resume.status({})` |

实现上：CLI handler 直接调 MCP tool 的 Python 函数，**零代码重复**。

### 3.4 CLI 输出格式

```bash
resume status                     # 人类可读
resume status --json              # 给脚本/CI 用
resume status --format markdown   # 嵌入 README
```

---

## 四、双层 SKILL.md（LLM-agnostic 方法论）

### 4.1 为什么需要

不是所有 agent 都支持 MCP。例如：
- 用户在 ChatGPT 网页版手动跑流程
- 用户用 Copilot Chat（部分版本未支持 MCP）
- 用户想把方法论喂给 Gemini 做研究

**双层 SKILL.md** 让任何 LLM 直接读懂"该怎么做"。

### 4.2 文件结构

```markdown
---
# === 上层：LLM-agnostic（任何 LLM 读都明白）===
skill_id: intake.dialog
schema_version: "2.0"
goal: 用 STAR 法则深挖一个项目经历
intent_triggers:
  zh: ["聊聊我的经历", "深挖一下", "深度访谈"]
  en: ["deep dive", "tell me about your project"]
inputs:
  - name: project_topic
    type: string
    optional: true
outputs:
  - profile/projects/<id>/data.yaml
  - profile/projects/<id>/narrative.md
principles: [truth_first, evidence_chain]
preconditions:
  - state.initialized: true
---

# /intake.dialog — 深挖经历（方法论）

## 你（LLM）的任务

用 STAR 法则一问一答地引导用户描述项目，**绝不替用户编造**。

## STAR 流程

| 阶段 | 问题模板 | 必拿到 |
|---|---|---|
| Situation | "这个项目背景？为什么做？" | 业务上下文 |
| Task     | "你具体负责什么？" | 你的角色与边界 |
| Action   | "你做了什么？用了什么技术？" | 技术细节 |
| Result   | "结果如何？数据呢？" | 量化成果 |

## 不要做的事

- ❌ 不要批量提问，一次只问一个
- ❌ 不要用"听起来很棒"这种空洞回应
- ❌ 不要在用户给不出量化数据时编造数字
- ❌ 不要跳过 STAR 任何一步

## 输出契约

当 STAR 四步全部收集到、且至少一个 achievement 有量化数据时：
1. 调用 `resume.intake.confirm` 工具（如果可用）
2. 否则按 schema 输出 yaml 文本，让用户保存到 `profile/projects/<id>/data.yaml`

---

# === 下层：agent-specific 实现（不同 agent 各取所需）===

## tool_calls

### claude_code / cursor / cline (有 MCP)
```yaml
- step: 启动深挖
  call: mcp.resume.intake.dialog
- step: 收集 STAR 后落盘
  call: mcp.resume.intake.confirm
```

### chatgpt / gemini (无 MCP, 走 CLI)
```yaml
- step: 让用户在本地跑
  cli: resume intake dialog
- step: 把 STAR 整理后导入
  cli: resume intake confirm --from-stdin
```

### 纯 LLM (无任何工具)
```yaml
- step: 按 schema 输出 yaml 文本
- step: 告诉用户保存到指定路径
- step: 告诉用户跑 `resume validate` 校验
```
```

### 4.3 分发

每份 SKILL.md 在三处使用：

| 位置 | 用途 |
|---|---|
| `resume_alchemist/skills/*.md` | 包内文档 |
| `~/.claude/skills/resume-alchemist/skills/*.md` | Claude Code 加载 |
| MCP `@mcp.prompt()` 注册 | 暴露给所有 MCP 客户端 |

修改时只改一处，构建脚本同步到其他位置。

---

## 五、Agent 适配的具体差异

### 5.1 Claude Code（原生）

- 加载 `~/.claude/skills/resume-alchemist/`
- 触发词解析直接由 Claude Code 完成
- 双通道：既可走原生 SKILL.md，也可走 MCP（推荐用 MCP，因为 tool 调用比 SKILL.md 内嵌的 Bash 更可控）

### 5.2 Cursor / Cline

- 主要走 MCP
- 可选：`.cursorrules` 里加一段 "如果用户提到简历/求职，请使用 resume-alchemist MCP server"

### 5.3 ChatGPT（Custom GPT）

挑战：ChatGPT Action 走 OpenAPI HTTP，不直接吃 stdio MCP。

方案：

```
ChatGPT  ──HTTP──→  MCP HTTP Gateway  ──MCP──→  resume serve
                    （resume serve --transport http）
```

`resume serve --transport http --port 7777` 暴露 OpenAPI（用 [mcp-openapi](https://github.com/...) 工具自动生成）。

用户:
1. 本地启动 `resume serve --transport http`
2. （可选）用 ngrok / cloudflare tunnel 暴露
3. 在 Custom GPT 的 Action 里配置该 URL

### 5.4 Gemini CLI / Codex / Continue

直接 stdio MCP，零额外工作。

### 5.5 纯 LLM（没有工具能力）

把 SKILL.md 内容直接当 system prompt 喂给 LLM，让它指导用户**手动**完成流程：

```
你是简历炼金术士的方法论 prompt（内容见 skills/intake.md 上层段）。
按 STAR 流程引导我，最后输出 yaml 内容让我保存。
```

LLM 不能写文件，但能产 yaml 文本。用户复制保存 + 跑 `resume validate` 即可。

---

## 六、安全 & 隐私

| 风险 | 缓解 |
|---|---|
| MCP server 监听端口被恶意访问 | stdio 默认；http/sse 强制 token；本地优先 |
| 简历含敏感信息（手机/身份证） | `.resume-cache/traces/` 自动脱敏；validator 警告 |
| LLM 看到的内容被发到外部 | 用户清楚 agent 用的是哪个 LLM；resume 不主动联网 |
| MCP tool 被滥用调用（例如 build 100 次） | rate-limit 中间件 |

---

## 七、可观测性

每个 MCP tool 调用都记录：

```
.resume-cache/traces/2026-06-30T10-00-00_intake_dialog.yaml
  - tool: intake.dialog
  - input: {...}
  - output: {...}
  - duration_ms: 234
  - agent: claude-code (sniffed from User-Agent)
  - llm_model: claude-opus-4 (if reported)
```

用户可：
- 跑 `resume traces list / show / replay`
- 把可疑 trace 上报 issue（敏感字段自动脱敏）

---

## 八、版本与发布

| 包 | 发布方式 |
|---|---|
| `resume-alchemist` (PyPI) | `pip install resume-alchemist` |
| `~/.claude/skills/resume-alchemist/` | install.sh 自动 symlink 包内 skills/ 目录 |
| MCP tools 的 schema | 跟随 pip 包版本，agent 端自动同步 |

---

## 九、迁移路径（从 v1 Claude Code-only 到 v2 跨 agent）

| 用户类型 | 升级动作 |
|---|---|
| v1 Claude Code 用户 | `pip install --upgrade resume-alchemist` → `resume migrate` → 继续用 Claude Code |
| 想试 Cursor | `pip install resume-alchemist` → 在 Cursor `mcp.json` 加配置 |
| 想 CI | `pip install resume-alchemist` → 跑 `resume validate` 当 lint |

**关键**：v1 用户**不需要重新学**——同样的触发词、同样的对话方式，底层换成 MCP 而已。

---

下一章：[05-skills-redesign.md](05-skills-redesign.md) — Skill 包 13 → 7 重构
