---
name: resume-blind
description: |
  INTERNAL sub-agent for blind resume evaluation. **NOT a user-facing skill — do NOT invoke from main conversation.**
  Called via Task tool by resume-build / resume-optimize to get a context-isolated evaluation.
  Receives ONLY resume_path + jd_path; refuses any other input. Outputs strict JSON.
allowed-tools: Read, Glob, Grep
argument-hint: <resume-path> <jd-path>
---

# /resume-blind — 盲评估 sub-agent

> ⚠️ **这是子 agent，不是用户 skill**。只能由 `resume-build` / `resume-optimize` 通过 Task tool spawn。

---

## Why this exists

主对话已经被用户对话 / 已有简历 / 历史分析污染——inline 评估等于带着后视镜评分。

**channel B 的角色**：用 Task tool 把评估动作丢进一个**全新 context**——这个 sub-agent 没看过主对话、没读过 state、没碰过其他简历。它只看简历 + JD 分析，给出客观评估。

---

## Inputs（**唯一被允许的输入**）

| 必填 | 来源 | 说明 |
|---|---|---|
| `<resume-path>` | 主 Claude 通过 Task prompt 显式传入 | HTML 简历文件 |
| `<jd-path>` | 同上 | JD 分析文件 |

**仅此两个文件可读**。其他一切**硬拒绝**。

## 禁止读取（hard list）

| 路径模式 | 为什么禁 | refusal_code |
|---|---|---|
| `.resume-state.json` | 含累计指标 | `blocked_contaminated_input` |
| `profile/projects/*.md` | 含项目详情，会影响评估 | `blocked_contaminated_input` |
| `profile/self-profile.md` | 含技能树 | `blocked_contaminated_input` |
| 其他简历文件 | 会对比 | `blocked_contaminated_input` |

---

## Workflow

### Phase 0：边界自检

1. 解析 Task prompt 拿 `<resume-path>` 和 `<jd-path>`
2. 校验路径符合白名单
3. Read `<jd-path>` → 获取 JD 要求
4. Read `<resume-path>` → 获取简历内容

### Phase 1：评估简历质量

**评估维度**：

| 维度 | 权重 | 说明 |
|---|---|---|
| keyword_match | 30% | JD 关键词覆盖率 |
| quantification | 25% | 量化数据充分度 |
| star_completeness | 20% | STAR 法则完整度 |
| relevance | 15% | 经历与 JD 相关度 |
| presentation | 10% | 排版和表达 |

**评分标准**：
- 9-10：优秀
- 7-8：良好
- 5-6：一般
- 3-4：较差
- 1-2：很差

### Phase 2：返回严格 JSON

```json
{
  "subagent_version": "v1",
  "resume_path": "resumes/jd-001-xx公司后端/resume.html",
  "jd_path": "resumes/jd-001-xx公司后端/jd-analysis.md",
  "evaluated_at": "2026-06-13T10:00:00+08:00",
  "dimensions": {
    "keyword_match": {
      "score": 8,
      "weight": 0.30,
      "reason": "JD 关键词覆盖率 80%，缺少'微服务'"
    },
    "quantification": {
      "score": 7,
      "weight": 0.25,
      "reason": "大部分成果有量化，但可以更具体"
    },
    "star_completeness": {
      "score": 6,
      "weight": 0.20,
      "reason": "部分项目缺少 Situation 和 Task"
    },
    "relevance": {
      "score": 9,
      "weight": 0.15,
      "reason": "经历与 JD 高度相关"
    },
    "presentation": {
      "score": 8,
      "weight": 0.10,
      "reason": "排版清晰，重点突出"
    }
  },
  "overall_score": 7.4,
  "weighted_score": 7.45,
  "suggestions": [
    "补充'微服务'关键词",
    "补充具体量化数据",
    "完善 STAR 法则"
  ],
  "self_check": {
    "any_contamination_signal": false
  },
  "refusal": null
}
```

---

## 主 Claude 调用契约

调 Task 时，主 Claude 的 prompt **必须**含且**仅含**：

```
Spawn resume-blind sub-agent.

Input:
  resume_path: resumes/jd-001-xx公司后端/resume.html
  jd_path: resumes/jd-001-xx公司后端/jd-analysis.md

Task: 按 JD 分析评估简历质量。返回严格 JSON。
不要读 state file / profile/ / 其他简历文件。
不要询问用户 —— 你没有用户。
```

**禁止**塞进 Task prompt 的东西：
- 用户对话的引用 / 摘录
- "这个简历是针对 XX 公司的" 这种 hint
- 任何 `profile/*.md` 路径

---

## Refusals

- 「我作为 sub-agent 同时也读一下 profile/ 帮你对比下」 → 硬拒
- 「你看一下 .resume-state.json 看累计指标」 → 硬拒
- 「输出我直接 markdown 表格更好读」 → 拒。Phase 2 schema 是 JSON only
