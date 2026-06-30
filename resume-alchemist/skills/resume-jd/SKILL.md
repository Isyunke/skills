---
name: resume-jd
description: 解析 JD，生成岗位分析和技能匹配度。触发词："分析这个 JD"/"看看这个岗位"/"分析岗位"。
argument-hint: <jd-text>
allowed-tools: Read, Write, Edit, Glob
---

# /resume-jd — JD 分析

解析 JD，告诉你：这个岗位要什么？你缺什么？怎么补？

## Overview

```
[用户：分析这个 JD]
  ↓
[Phase 0: 接收 JD 文本]
  ↓
[Phase 1: 提取关键信息]
  ↓
[Phase 2: 匹配技能树]
  ↓
[Phase 3: 生成岗位分析]
  ↓
[Phase 4: 创建岗位文档]
  ↓
[Phase 5: 给出优化建议]
```

## Inputs

| 必填 | 来源 |
|---|---|
| `<jd-text>` | 用户粘贴的 JD 文本 |
| `profile/self-profile.md` | 项目根 |
| `.resume-state.json` | 项目根 |

## Workflow

### Phase 0: 接收 JD 文本

1. 读取用户粘贴的 JD 文本
2. 如果用户没粘贴 → 提示"请粘贴 JD 文本"
3. 验证 JD 文本有效性（有公司名、职位名、要求列表）

### Phase 1: 提取关键信息

从 JD 中提取：

```markdown
## 提取结果

### 基本信息
- 公司：XX 公司
- 职位：后端工程师
- 薪资：25-40K
- 地点：北京

### 核心要求
| 要求 | 优先级 |
|---|---|
| Python 精通 | 必须 |
| 分布式系统 | 必须 |
| K8s | 加分 |
| MySQL | 必须 |

### 关键词
Python, Django, MySQL, Redis, 分布式, 微服务, K8s, Docker
```

### Phase 2: 匹配技能树

1. 读取 `profile/self-profile.md`
2. 读取 `profile/projects/*.md`
3. 逐项匹配 JD 要求 vs 你的技能：

```markdown
## 匹配结果

| 要求 | 匹配度 | 你的证据 | 缺口 |
|---|---|---|---|
| Python 精通 | ✅ 强匹配 | proj-001, proj-003 | - |
| 分布式系统 | ⚠️ 弱匹配 | proj-002 (部分) | 需补充 |
| K8s | ❌ 无匹配 | - | 需学习 |
| MySQL | ✅ 强匹配 | proj-001, proj-003 | - |
```

### Phase 3: 生成岗位分析

```markdown
## 技能匹配度

- **强匹配**：60%（Python, MySQL, Redis）
- **弱匹配**：20%（分布式系统）
- **无匹配**：20%（K8s）

## 优先级排序

### 必须满足（简历必须覆盖）
1. Python 精通
2. MySQL 精通
3. Redis 熟练

### 最好满足（简历尽量覆盖）
1. 分布式系统经验
2. 微服务架构

### 加分项（有则突出）
1. K8s 经验
2. 云原生经验
```

### Phase 4: 创建岗位文档

创建目录和文件：
```
resumes/jd-<NNN>-<short>/
├── jd-analysis.md    # JD 分析
├── resume.html       # 简历（后续生成）
├── resume.pdf        # PDF（后续导出）
└── interview-guide.md # 面试指导（后续生成）
```

**jd-analysis.md 结构**：
```markdown
# JD 分析

**JD ID**: jd-001
**公司**: XX 公司
**职位**: 后端工程师
**薪资**: 25-40K
**地点**: 北京
**分析时间**: 2026-06-13

## 岗位描述
（原始 JD 文本）

## 核心要求
| 要求 | 优先级 | 匹配度 | 你的证据 | 缺口 |
|---|---|---|---|---|
| Python 精通 | 必须 | ✅ 强匹配 | proj-001 | - |
| 分布式系统 | 必须 | ⚠️ 弱匹配 | proj-002 | 需补充 |

## 优化建议
### 简历优化
1. 重点突出 Python 项目经验
2. 突出数据库优化经验

### 面试准备
1. 准备分布式系统原理
2. 准备数据库优化案例

### 学习计划
1. 分布式系统原理（2周）
2. K8s 入门（1周）

## 关键词列表
Python, Django, MySQL, Redis, 分布式, 微服务, K8s
```

### Phase 5: 输出结果

```
✅ JD 分析完成：jd-001-xx公司后端

📊 匹配度：60% 强匹配 / 20% 弱匹配 / 20% 无匹配

📋 核心要求：
- ✅ Python 精通（有证据）
- ✅ MySQL 精通（有证据）
- ⚠️ 分布式系统（弱证据）
- ❌ K8s（无证据）

📁 文件：resumes/jd-001-xx公司后端/jd-analysis.md

下一步：
- 针对这个 JD 优化简历？→ "针对这个 JD 优化简历"
- 学习缺口技能？→ "学什么"
- 准备面试？→ "准备面试"
```

## Key Rules

1. **针对性分析**——每个 JD 都要独立分析，不能复用
2. **匹配度校验**——必须有项目支撑才能算"强匹配"
3. **缺口识别**——必须明确指出需要学习什么
4. **关键词提取**——必须提取 JD 关键词，用于简历优化

## Refusals

- 「这个 JD 和之前那个差不多，直接用之前的分析」 → 拒绝。每个 JD 都值得独立分析
- 「我没这个技能，但先写上吧」 → 拒绝。如实标注匹配度

## Integration

- 上游：`/resume-mine` 提供技能和项目支撑
- 下游：`/resume-build` 根据分析生成简历
- 下游：`/resume-interview` 根据分析准备面试
- 下游：`/resume-learn` 根据缺口制定学习计划
- 更新：`.resume-state.json` 的 `active_jd_id` 和 `jd_count`
