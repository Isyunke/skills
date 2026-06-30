# 🧪 Resume Alchemist v2 — 重构方案索引

> 本目录是 v2 全面重构的设计文档集合，分章节维护，便于逐步演进。
>
> **状态**：📐 设计中（草案）
> **基线版本**：v1.3.0
> **目标版本**：v2.0.0
> **兼容要求**：v1 用户的 `.resume-state.json` 与档案数据**完全无缝迁移**
> **技术栈**：Python 3.10+ core / Jinja2 / Pydantic v2 / MCP SDK (Python) / Click CLI

---

## 这次重构要解决的根本问题

v1 的方向是对的——「深挖经历 → 分析 JD → 定制简历 → 面试 → 学习」的闭环+三条不可妥协原则确实是同类产品没有的差异化。但 v1 有 5 个**结构性瓶颈**让它无法兑现承诺：

| # | 瓶颈 | 后果 |
|---|---|---|
| 1 | 深度绑定 Claude Code（SKILL.md / Bash hook / Task tool） | 出了 Claude Code 就是死字，无法"任何 agent + 任何 LLM" |
| 2 | 数据层全是非结构化 Markdown | 证据链/匹配度只能让 LLM 每次重算，无法程序化校验 |
| 3 | Hook 强制层只警告不阻止，且依赖 grep | 三条"不可妥协"原则在工程上是可妥协的 |
| 4 | LLM 当模板渲染器 | 简历样式漂移、token 浪费、不可复现 |
| 5 | 没有反馈闭环 | 用户投了哪份简历、通过没、为什么没通过——系统一无所知 |

v2 的目标是**逐一拔掉这 5 个瓶颈**，同时保留 v1 的灵魂（三条原则 + 5 阶段闭环 + 鼓励但不谄媚的 voice）。

---

## 文档索引

| 章节 | 文件 | 主题 | 关键产物 |
|---|---|---|---|
| 00 | [00-vision-and-diagnosis.md](00-vision-and-diagnosis.md) | 愿景重述 + v1 详细诊断 | 5 大瓶颈深度剖析、保留 vs 重做清单 |
| 01 | [01-architecture-7layers.md](01-architecture-7layers.md) | 7 层架构总图 | 架构图、层间契约、依赖方向 |
| 02 | [02-data-layer-spec.md](02-data-layer-spec.md) | 知识档案层（KB）规范 | `data.yaml` schema、双轨制（结构化+叙事）、JSON Resume 互操作 |
| 03 | [03-tools-layer-spec.md](03-tools-layer-spec.md) | 确定性工具层 | `evidence_validator` / `match_scorer` / `renderer` 等核心工具 spec |
| 04 | [04-mcp-cross-agent.md](04-mcp-cross-agent.md) | 跨 agent 适配层 | MCP server 协议、CLI 入口、Claude Code 适配 |
| 05 | [05-skills-redesign.md](05-skills-redesign.md) | Skill 包重构 | 13 → 7 核心 skill 的合并方案、双层文档结构 |
| 06 | [06-feedback-loop.md](06-feedback-loop.md) | 反馈闭环层 | `outcomes.yaml`、dashboard、ROI 分析、coach 角色化 |
| 07 | [07-ux-improvements.md](07-ux-improvements.md) | 交互人性化 | onboarding 重做、diff 视图、show-me 模式、交互式面试 |
| 08 | [08-migration-v1-to-v2.md](08-migration-v1-to-v2.md) | v1→v2 迁移规范 | 字段映射、自动迁移脚本、回退方案 |
| 09 | [09-roadmap.md](09-roadmap.md) | 分期落地路线图 | P0/P1/P2/P3 任务分解、验收标准、风险登记 |

---

## 阅读建议

- **想看大方向** → 读 00 + 01
- **想看技术决策** → 读 02 + 03 + 04
- **想看产品改动** → 读 05 + 06 + 07
- **想动手实施** → 读 08 + 09

---

## v2 设计原则（贯穿全文）

1. **结构化优先，叙事兜底**：所有事实存 yaml，给 LLM/人类看的 markdown 由模板渲染生成。
2. **代码能干的不让 LLM 干**：关键词提取、匹配度计算、证据链校验、HTML 渲染——都用代码。
3. **LLM 只干它擅长的**：理解、共情、追问、改写、评分。
4. **跨 agent 一等公民**：MCP 协议是头等输出，Claude Code 只是其中一个 host。
5. **可观测可反馈**：每个动作记日志、用户结果回流、dashboard 驱动下次迭代。
6. **完全向后兼容**：v1 用户跑一次 `resume migrate` 就能用 v2，所有历史数据保留。

---

## 这份方案不做什么

- ❌ 不引入第二门语言（避免运维负担）
- ❌ 不引入云服务依赖（必须能完全离线运行）
- ❌ 不要求用户改变工作流（核心仍是"对话式"）
- ❌ 不削弱三条不可妥协原则（只会让它们在工程上更硬）
- ❌ 不为了酷炫加 NLP/AI 黑科技（语义嵌入是可选项，不是必选）
