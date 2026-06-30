---
name: resume-profile
description: 维护用户的技能树，标注证据强度。触发词："看看我的技能树"/"我的技能"/"技能清单"。
argument-hint: none
allowed-tools: Read, Write, Edit, Glob
---

# /resume-profile — 技能树管理

维护你的技能树，标注证据强度。让你知道自己会什么、不会什么。

## Overview

```
[用户：看看我的技能树]
  ↓
[Phase 0: 读取 self-profile.md]
  ↓
[Phase 1: 分析技能树]
  ↓
[Phase 2: 显示技能树]
  ↓
[Phase 3: 给出建议]
```

## Inputs

| 必填 | 来源 |
|---|---|
| `profile/self-profile.md` | 项目根 |
| `profile/projects/*.md` | 项目根 |

## Workflow

### Phase 0: 读取 self-profile.md

1. 读取 `profile/self-profile.md`
2. 读取 `profile/projects/*.md`
3. 分析技能证据

### Phase 1: 分析技能树

```python
# 分析技能证据
for skill in skills:
    evidence = find_evidence(skill, projects)
    if evidence:
        skill.evidence_strength = "🟢 强"
    else:
        skill.evidence_strength = "🔴 无"
```

### Phase 2: 显示技能树

```
📊 技能树

## 编程语言
| 技能 | 熟练度 | 评分 | 证据 | 证据强度 |
|---|---|---|---|---|
| Python | 精通 | 8/10 | proj-001, proj-003 | 🟢 强 |
| Java | 熟练 | 6/10 | proj-002 | 🟢 强 |
| Go | 了解 | 3/10 | - | 🔴 无 |

## 框架
| 技能 | 熟练度 | 评分 | 证据 | 证据强度 |
|---|---|---|---|---|
| Django | 精通 | 7/10 | proj-001 | 🟢 强 |
| Spring Boot | 熟练 | 5/10 | proj-002 | 🟢 强 |

## 数据库
| 技能 | 熟练度 | 评分 | 证据 | 证据强度 |
|---|---|---|---|---|
| MySQL | 精通 | 8/10 | proj-001, proj-003 | 🟢 强 |
| Redis | 熟练 | 6/10 | proj-001 | 🟢 强 |

## 工具
| 技能 | 熟练度 | 评分 | 证据 | 证据强度 |
|---|---|---|---|---|
| Git | 精通 | 8/10 | 所有项目 | 🟢 强 |
| Docker | 熟练 | 6/10 | proj-001 | 🟢 强 |

## 软技能
| 技能 | 熟练度 | 评分 | 证据 | 证据强度 |
|---|---|---|---|---|
| 项目管理 | 熟练 | 7/10 | work-001 | 🟢 强 |
| 沟通协调 | 精通 | 8/10 | work-002 | 🟢 强 |
```

### Phase 3: 给出建议

```
💡 技能树分析

📊 统计：
- 总技能：12 项
- 有证据：10 项（83%）
- 无证据：2 项（17%）

⚠️ 无证据技能：
- Go（了解）：建议补充项目或学习
- K8s（了解）：建议补充项目或学习

🎯 建议：
1. 补充 Go 项目经验
2. 学习 K8s 基础
3. 深挖更多项目经历

下一步：
- 深挖经历？→ "聊聊我的经历"
- 学习技能？→ "学什么"
- 分析 JD？→ "分析这个 JD"
```

## Key Rules

1. **证据校验**——有项目支撑才能提升熟练度
2. **实时更新**——深挖经历后自动更新
3. **可视化**——用表格和 emoji 直观展示

## Integration

- 上游：`/resume-mine` 提供项目和技能
- 下游：`/resume-jd` 匹配 JD 要求
- 下游：`/resume-build` 生成简历
