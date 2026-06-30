---
name: resume-mine
description: 通过对话式引导，挖掘用户的项目和工作经历。触发词："聊聊我的经历"/"深挖一下"/"更新项目"/"补充经历"。
argument-hint: [project-name]
allowed-tools: Read, Write, Edit, Glob
---

# /resume-mine — 深挖经历

通过对话式引导，挖掘你都没意识到的闪光点。

## Overview

```
[用户：聊聊我的经历]
  ↓
[Phase 0: 读取 self-profile.md]
  ↓
[Phase 1: 引导式提问（STAR 法则）]
  ↓
[Phase 2: 提取关键信息]
  ↓
[Phase 3: 生成/更新 project.md]
  ↓
[Phase 4: 更新 self-profile.md]
  ↓
[Phase 5: 给出下一步建议]
```

## Constants

- **STAR_METHOD = true** — 默认使用 STAR 法则引导
- **QUANTIFY = true** — 默认要求量化成果

## Inputs

| 必填 | 来源 |
|---|---|
| 用户口述 | 对话 |
| `profile/self-profile.md` | 项目根 |
| `.resume-state.json` | 项目根 |

## Workflow

### Phase 0: 读取现有档案

1. 读 `.resume-state.json` → 不存在则路由到 `/resume-init`
2. 读 `profile/self-profile.md` → 了解已有技能和经历
3. 读 `profile/projects/` → 了解已有项目
4. 决定深挖方向：
   - 无项目 → 从最近的工作/项目开始
   - 有项目 → 问"要更新哪个项目？还是聊新的？"

### Phase 1: 引导式提问（STAR 法则）

**破冰**：
```
聊聊你最近做过的项目？
或者，你最自豪的一个项目是什么？
```

**深挖（STAR 法则）**：

| 阶段 | 问题 | 目的 |
|---|---|---|
| **S**ituation | "这个项目背景是什么？为什么做这个？" | 了解业务场景 |
| **T**ask | "你具体负责什么？你的任务是什么？" | 明确贡献范围 |
| **A**ction | "你做了什么？怎么做的？用了什么技术？" | 了解具体工作 |
| **R**esult | "结果如何？有数据吗？性能提升了多少？" | 量化成果 |

**追问技巧**：
- "能再具体一点吗？"
- "有数据支撑吗？"
- "遇到什么困难？怎么解决的？"
- "如果重来，你会怎么做？"

### Phase 2: 提取关键信息

从对话中提取：

```markdown
## 提取结果

### 项目信息
- 项目名称：XX
- 时间：2024.01 - 2024.06
- 角色：后端开发
- 团队：5人

### STAR
- Situation：...
- Task：...
- Action：...
- Result：...

### 技术栈
- 语言：Python
- 框架：Django
- 数据库：MySQL

### 技能标签
- Python (精通)
- Django (熟练)

### 量化成果
- 性能提升 50%
- 用户量增长 100%
```

### Phase 3: 生成/更新 project.md

**新建项目**：
```bash
# 文件名：proj-<NNN>-<short>.md
profile/projects/proj-001-xx系统.md
```

**更新项目**：
- 读取现有 project.md
- 合并新信息
- 原子写：.tmp → rename

**project.md 结构**：
```markdown
# [项目名称]

**项目 ID**: proj-001
**时间**: 2024.01 - 2024.06
**角色**: 后端开发

## 项目背景
（Situation）

## 我的职责
（Task）

## 技术方案
- 语言：Python
- 框架：Django

## 具体工作
（Action）

## 项目成果
（Result - 量化！）

## 技能标签
| 技能 | 熟练度 | 证据强度 |
|---|---|---|
| Python | 精通 | 🟢 强 |

## 面试要点
- 最大挑战：...
- 解决方案：...
```

### Phase 4: 更新 self-profile.md

1. 读取 `profile/self-profile.md`
2. 更新技能树：
   - 新增技能 → 添加
   - 已有技能 → 更新熟练度/证据
3. 更新项目经历列表
4. 原子写：.tmp → rename

**更新规则**：
- 不覆盖，只追加或修改
- 证据强度校验：有项目支撑才能提升熟练度
- 原子写：使用 .tmp → rename

### Phase 5: 输出结果

```
✅ 项目已记录：proj-001-xx系统

📊 技能更新：
- Python: 熟练 → 精通 (新增证据)
- Django: 新增 (熟练)

📁 文件：
- profile/projects/proj-001-xx系统.md
- profile/self-profile.md (已更新)

下一步：
- 继续深挖其他项目？→ "聊聊另一个项目"
- 分析 JD？→ "分析这个 JD [粘贴 JD]"
- 看看技能树？→ "看看我的技能树"
```

## Key Rules

1. **STAR 法则**——每个项目都要走 Situation → Task → Action → Result
2. **量化成果**——必须问"有数据吗？"，不能只说"提升了性能"
3. **证据强度**——有项目支撑才能提升熟练度
4. **原子写**——所有文件更新使用 .tmp → rename
5. **不虚构**——只记录用户真实描述，不帮用户编造

## Refusals

- 「帮我编一段项目经历」 → 拒绝。简历炼金术士只炼真金
- 「我没数据，随便写一个」 → 拒绝。可以估算，但不能虚构
- 「这个项目不是我做的，但我想写上」 → 拒绝。只记录你的真实贡献

## Integration

- 上游：`/resume-init` 创建初始档案
- 下游：`/resume-profile` 查看技能树
- 下游：`/resume-jd` 分析 JD 时会读取项目文档
- 下游：`/resume-build` 生成简历时会读取项目文档
