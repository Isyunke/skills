---
name: resume-status
description: 显示当前项目状态。触发词："状态"/"进度"/"看板"。
argument-hint: none
allowed-tools: Read, Glob
---

# /resume-status — 状态看板

显示当前项目状态，让你知道：做了什么、还差什么。

## Overview

```
[用户：状态]
  ↓
[Phase 0: 读取状态文件]
  ↓
[Phase 1: 统计数据]
  ↓
[Phase 2: 显示看板]
```

## Inputs

| 必填 | 来源 |
|---|---|
| `.resume-state.json` | 项目根 |
| `profile/projects/*.md` | 项目根 |
| `resumes/*/jd-analysis.md` | 项目根 |

## Workflow

### Phase 0: 读取状态文件

1. 读取 `.resume-state.json`
2. 读取 `profile/projects/*.md`
3. 读取 `resumes/*/jd-analysis.md`
4. 读取 `learning/*/learning-guide.md`

### Phase 1: 统计数据

```python
# 统计项目数量
project_count = len(glob("profile/projects/*.md"))

# 统计 JD 数量
jd_count = len(glob("resumes/*/jd-analysis.md"))

# 统计简历数量
resume_count = len(glob("resumes/*/resume.html"))

# 统计学习计划数量
learning_count = len(glob("learning/*/learning-guide.md"))
```

### Phase 2: 显示看板

```
📊 简历炼金术士 — 状态看板

🎯 目标：[职位] / [行业] / [经验]

📁 数据统计：
- 项目经历：3 个
- 技能数量：12 项
- JD 分析：2 个
- 简历数量：2 份
- 学习计划：1 个

⏰ 最近活动：
- 最后深挖：2026-06-10
- 最后 JD 分析：2026-06-12
- 最后简历生成：2026-06-12
- 最后面试准备：2026-06-13

📋 待办事项：
- [ ] 学习分布式系统（进行中）
- [ ] 学习 K8s（待开始）

🎯 当前 JD：jd-001-xx公司后端
- 匹配度：60% 强匹配
- 缺口：分布式系统、K8s

📁 文件结构：
profile/
├── self-profile.md
├── projects/
│   ├── proj-001-xx系统.md
│   ├── proj-002-yy平台.md
│   └── proj-003-zz工具.md
└── work-history/
    └── company-001-xx公司.md

resumes/
├── jd-001-xx公司后端/
│   ├── jd-analysis.md
│   ├── resume.html
│   └── interview-guide.md
└── jd-002-yy公司全栈/
    └── jd-analysis.md

learning/
├── learning-overview.md
└── skill-001-分布式系统/
    └── learning-guide.md
```

## Key Rules

1. **实时性**——状态必须是最新的
2. **完整性**——显示所有关键指标
3. **可操作性**——给出下一步建议

## Integration

- 读取：所有子 skill 的输出
- 显示：当前项目状态
