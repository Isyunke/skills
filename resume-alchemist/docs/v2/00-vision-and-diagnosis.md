# 00 · 愿景重述与 v1 诊断

## 一、回到原点：Resume Alchemist 到底要解决什么

剥掉所有口号和 slogan，这个项目的核心命题是：

> **让一个普通求职者，借助 AI，把自己的真实经历"工程化"地匹配到目标岗位上，并形成持续优化的闭环。**

拆解：

| 关键词 | 含义 | v1 已经做到？ |
|---|---|---|
| **普通求职者** | 不是简历专家，不会 prompt engineering，可能没耐心 | ⚠️ 部分（onboarding 还行，但日常交互依赖记触发词） |
| **借助 AI** | 用任何主流 LLM、任何 agent 都行 | ❌ 只能在 Claude Code 跑 |
| **真实经历** | 三条原则的底线 | ⚠️ 文档说了，工程没卡死 |
| **工程化** | 可复现、可校验、可 diff、可回滚 | ❌ 全是自由文本 |
| **匹配** | JD → 经历的双向校准 | ⚠️ 算法弱（grep 关键词） |
| **闭环** | 投递结果 → 反向优化 | ❌ 完全缺失 |

也就是说——**愿景是好的，落地只完成了 30%**。v2 要把剩下的 70% 补齐。

---

## 二、v1 必须保留的好东西

不是全推倒。下面这些是 v1 的"魂"，v2 必须**原样保留或者强化**：

### 2.1 三条不可妥协原则
真实性 / 针对性 / 证据链。这是与"通用 ChatGPT 帮写简历"的核心差异化。**v2 不削弱，只增强工程强制。**

### 2.2 5 阶段闭环方法论
```
深挖经历 → 分析 JD → 定制简历 → 面试准备 → 学习补充
```
方法论本身没问题，v2 只是把每个阶段做扎实。

### 2.3 STAR + 量化的叙事范式
所有项目走 Situation/Task/Action/Result + 量化数据。**v2 把这个范式落到 schema 字段层。**

### 2.4 盲评估 sub-agent 的 context 隔离思想
[resume-blind](../../skills/resume-blind/SKILL.md) 用全新 context 评估、只能读 resume+jd 两个文件——这是非常成熟的系统思维。**v2 把它升级为通用的"隔离评估协议"，不止评简历。**

### 2.5 "鼓励但不谄媚"的 voice
> "直接指出问题：你的简历缺少量化数据"
> "不要用模糊措辞软化"

这种 voice 写得非常克制、有用、不油腻。**v2 全文沿用。**

### 2.6 每个 JD 独立目录的存档结构
`resumes/jd-001-xx/` 这个组织方式很合理（一个 JD = 一个工作单元 = 简历+分析+面试指导+PDF）。**v2 保留，并扩展为 `outcomes.yaml`。**

---

## 三、v1 必须重做的部分

### 3.1 数据层（重做幅度：🔴 大）

**现状**：
- `profile/projects/proj-001.md` 是自由 markdown
- `self-profile.md` 用 markdown 表格存技能树
- `jd-analysis.md` 用 markdown 段落存岗位分析

**问题**：
- LLM 每次都得重新解析 → 不确定性、token 浪费
- 没法做"这个简历有几个量化数据"这种简单统计
- 多人协作/多设备同步时 markdown 排版被打乱
- 想做"导出 JSON Resume"或"接入 ATS"——根本无从下手

**v2 方案**：
- 每个实体（project / profile / jd / resume / outcome）都有 `data.yaml` 作为**单一事实来源**
- `narrative.md` 由 yaml + 模板渲染生成，**可重新生成**
- yaml 用 Pydantic v2 严格校验，schema 写死

详见 [02-data-layer-spec.md](02-data-layer-spec.md)。

### 3.2 工具层（重做幅度：🟡 中）

**现状**：
- [keyword_matcher.py](../../tools/keyword_matcher.py)：硬编码 150 个关键词
- [html_to_pdf.py](../../tools/html_to_pdf.py)：能用但脆弱
- [resume_parser.py](../../tools/resume_parser.py)：正则解析，碰到复杂排版就废
- 没有 `evidence_validator.py`、没有 `match_scorer.py`、没有 `renderer.py`

**v2 方案**：
- 新增 5 个核心工具（详见 [03-tools-layer-spec.md](03-tools-layer-spec.md)）
- 每个工具有清晰输入输出（JSON in / JSON out），方便 LLM 调用
- 可选项：`match_scorer` 支持 sentence-transformers 做语义匹配（不安装时降级为关键词匹配）

### 3.3 Hook 强制层（重做幅度：🔴 大）

**现状**：
- [truth-verification.sh](../../hooks/truth-verification.sh) 大多 `exit 0`
- [evidence-chain.sh](../../hooks/evidence-chain.sh) 只 grep 关键词
- 是 bash 脚本，Windows 用户体验差
- 是 Claude Code 私有机制，跨 agent 不可用

**v2 方案**：
- 移除 bash hook，改为 **`tools/evidence_validator.py`**（Python，跨平台）
- 在 `resume build` 流程内强制调用，校验失败**真·阻断**
- MCP server 中也强制走同一个 validator
- 详见 [03-tools-layer-spec.md](03-tools-layer-spec.md)

### 3.4 跨 agent 支持（重做幅度：🔴 大，新增）

**现状**：完全没有。

**v2 方案**：
- 提供 **MCP Server**，让 ChatGPT/Cursor/Cline/Copilot/Claude Desktop 都能用
- 提供 **CLI**（`resume` 命令），脚本和 CI 可用
- 提供 **双层 SKILL.md**：上层 LLM-agnostic 的方法论 prompt + 下层 agent-specific 的工具调用
- 详见 [04-mcp-cross-agent.md](04-mcp-cross-agent.md)

### 3.5 反馈闭环（重做幅度：🔴 大，新增）

**现状**：完全没有。系统不知道用户投了简历后发生了什么。

**v2 方案**：
- 新增 `outcomes.yaml`：记录投递、面试邀请、面试反馈、Offer
- 新增 `resume track` skill：引导用户回传结果
- `resume status` 升级为真·dashboard：投递→邀请→Offer 漏斗、最高 ROI 简历、最常被追问的弱点
- 详见 [06-feedback-loop.md](06-feedback-loop.md)

---

## 四、v1 现状的量化诊断

| 维度 | v1 状态 | v2 目标 |
|---|---|---|
| 支持的 agent 数 | 1（Claude Code） | 5+（Claude Code / Cursor / Cline / ChatGPT / Copilot Chat / CLI） |
| 结构化数据覆盖率 | 0%（全 markdown） | 100%（所有事实存 yaml） |
| Hook 真实阻断率 | ~5%（绝大多数 exit 0） | 100%（违规必拒，含 actionable 修复指引） |
| 单元测试数 | 3 | 30+ |
| 端到端测试数 | 0 | 5（覆盖 5 阶段闭环各一个） |
| Schema 版本管理 | 定义了 registry，未实现 migration | 真正可跑的 `resume migrate` |
| 反馈数据 | 无 | `outcomes.yaml` + dashboard |
| 文档语言 | 仅中文 | 中文 + 英文（核心 schema 双语） |

---

## 五、用户视角的"v2 应该是什么样"

下面是 v2 上线后用户的理想旅程，用对话形式描述：

### 场景 A：完全新用户（在 ChatGPT 里）

```
用户：（贴一个 MCP server 链接到 ChatGPT settings）
用户：帮我用 resume-alchemist 做求职准备
ChatGPT：[调用 mcp.resume.init]
        🧪 简历炼金术士已就绪。先问你 1 个问题：
        你现在的状态是？
        a) 有现成简历，想优化  b) 完全从零开始  c) 看到一个 JD 想看自己合不合适
用户：a
ChatGPT：把简历文件拖给我（PDF/DOCX/MD 都行）。
用户：[拖入 resume.pdf]
ChatGPT：[调用 mcp.resume.intake mode=file]
        ✅ 解析成功，识别出 3 个项目、12 项技能。
        但 2 项标"精通"的技能没有项目支撑，按真实性原则我标灰了。
        要现在补充一下吗？
```

→ 同一套 MCP server，明天他换到 Cursor 里，对话从上次断点继续。

### 场景 B：v1 老用户升级

```
用户：(在 Claude Code 里) /resume-status
Claude：检测到 v1 数据（schema_version=1.0），是否迁移到 v2？
        - 3 个项目 → 转换为 data.yaml + narrative.md
        - 2 份简历 → 保留原文件 + 新增 resume.yaml
        - 你的所有原文件会保留备份在 .resume-backup-v1/
用户：迁移
Claude：[运行 resume migrate]
        ✅ 迁移完成，无数据丢失。
        新增能力：
        - resume track（投递结果记录）
        - resume show me（即时查看任何档案）
        - 跨 agent 使用（启动 MCP server: resume serve）
```

### 场景 C：投了简历之后

```
用户：上周投的拉勾那个简历，HR 说我 K8s 经验不够，直接拒了
Claude：[调用 resume track]
        ✅ 已记录到 jd-005-拉勾后端/outcomes.yaml：
        - status: rejected
        - reason: "K8s 经验不足"
        - source: HR 反馈

        基于你最近 4 次投递的数据：
        - "K8s 经验不足" 被提到 3 次
        - "分布式系统" 被追问没答好 2 次

        建议：
        a) 优先补 K8s（最高 ROI）→ resume learn K8s
        b) 调整简历策略，避开重 K8s 的岗位
        c) 加强分布式系统的面试准备 → resume interview practice
```

这才是闭环。

---

## 六、不在 v2 范围内的事

为了避免 scope creep，下面这些**明确不做**：

- ❌ 内容农场式的"AI 模拟面试 100 套真题"
- ❌ 自动投递简历（违反招聘平台 ToS，也不是这个工具的定位）
- ❌ 内推/求职社交功能
- ❌ 招聘市场分析（薪资数据、行业趋势）—— 这是另一个 vertical
- ❌ Web 前端（CLI + MCP + 各家 agent 的原生 UI 已经足够）
- ❌ 多用户云端存储（v2 仍是本地优先 + git）

这些都是好功能，但不是 resume-alchemist 的核心定位。

---

下一章：[01-architecture-7layers.md](01-architecture-7layers.md)
