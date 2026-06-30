---
name: resume-learn
description: 分析技能缺口，制定学习计划。触发词："这个技能我不会"/"学什么"/"技能缺口"/"学习计划"。
argument-hint: [skill-name]
allowed-tools: Read, Write, Edit, Glob
---

# /resume-learn — 学习指导

分析技能缺口，制定学习计划。让你知道学什么、怎么学。

## Overview

```
[用户：这个技能我不会]
  ↓
[Phase 0: 读取 JD 分析 + 技能树]
  ↓
[Phase 1: 识别技能缺口]
  ↓
[Phase 2: 制定学习计划]
  ↓
[Phase 3: 推荐学习资源]
  ↓
[Phase 4: 创建学习文档]
  ↓
[Phase 5: 更新技能树]
```

## Inputs

| 必填 | 来源 |
|---|---|
| JD 分析 | `resumes/jd-<NNN>-<short>/jd-analysis.md` |
| 技能树 | `profile/self-profile.md` |

## Workflow

### Phase 0: 读取必要文件

1. 读取 `.resume-state.json` → 获取 `active_jd_id`
2. 读取 `resumes/jd-<NNN>-<short>/jd-analysis.md` → 获取技能缺口
3. 读取 `profile/self-profile.md` → 获取当前技能

### Phase 1: 识别技能缺口

从 JD 分析中提取缺口：

```markdown
## 技能缺口

| 技能 | 优先级 | 当前状态 | 目标状态 |
|---|---|---|---|
| 分布式系统 | 高 | ⚠️ 弱匹配 | ✅ 强匹配 |
| K8s | 中 | ❌ 无匹配 | ⚠️ 弱匹配 |
| 微服务 | 中 | ❌ 无匹配 | ⚠️ 弱匹配 |
```

### Phase 2: 制定学习计划

根据缺口制定学习计划：

```markdown
# 学习计划：分布式系统

## 为什么学

### JD 要求
- JD 中要求：分布式系统经验
- 当前状态：仅有部分经验
- 匹配度：⚠️ 弱匹配

### 职业发展
- 分布式系统是后端工程师的核心技能
- 掌握分布式系统可以提升竞争力

### 学习目标
- 理解分布式系统的基本概念
- 掌握分布式系统的常见架构
- 能够设计简单的分布式系统

## 学习路径

### 阶段 1：理论基础（Day 1-3）

**目标**：理解分布式系统的基本概念

**内容**：
1. CAP 理论
2. 一致性协议（Paxos, Raft）
3. 分布式存储

**验证**：
- [ ] 能解释 CAP 理论
- [ ] 能解释 Raft 协议
- [ ] 能画出分布式存储架构图

### 阶段 2：实践项目（Day 4-7）

**目标**：通过实践加深理解

**项目**：
1. 搭建简单的分布式 KV
2. 实现分布式锁

**验证**：
- [ ] 完成分布式 KV 项目
- [ ] 完成分布式锁项目

### 阶段 3：深入理解（Day 8-10）

**目标**：深入理解分布式系统的挑战

**内容**：
1. 分布式事务
2. 微服务架构

**验证**：
- [ ] 能解释分布式事务
- [ ] 能设计微服务架构

### 阶段 4：项目整合（Day 11-14）

**目标**：将学习成果应用到实际项目

**内容**：
1. 重构现有项目
2. 准备面试

**验证**：
- [ ] 完成项目重构
- [ ] 准备好面试回答
```

### Phase 3: 推荐学习资源

```markdown
## 推荐资源

### 书籍
- 《分布式系统：概念与设计》
- 《数据密集型应用系统设计》

### 课程
- MIT 6.824
- Coursera: Distributed Systems

### 项目
- etcd 源码阅读
- TiKV 源码阅读

### 博客
- The Paper Trail
- Martin Kleppmann's Blog
```

### Phase 4: 创建学习文档

创建目录和文件：
```
learning/
├── learning-overview.md          # 学习总览
├── skill-001-分布式系统/
│   ├── learning-guide.md         # 学习指导
│   ├── resources.md              # 学习资源
│   └── practice-projects.md      # 实践项目
```

### Phase 5: 更新技能树

1. 读取 `profile/self-profile.md`
2. 在技能树中标注"学习中"
3. 原子写：.tmp → rename

```
✅ 学习计划已生成：learning/skill-001-分布式系统/

📋 内容：
- 学习路径：4 个阶段，14 天
- 学习资源：3 本书、2 门课程、2 个项目
- 实践项目：2 个

📁 文件：
- learning/learning-overview.md
- learning/skill-001-分布式系统/learning-guide.md
- learning/skill-001-分布式系统/resources.md
- learning/skill-001-分布式系统/practice-projects.md

💡 学完后：
- 更新技能树？→ "更新技能树"
- 针对 JD 优化简历？→ "针对这个 JD 优化简历"
```

## Key Rules

1. **针对性**——学习计划必须针对特定 JD 缺口
2. **可执行**——学习路径必须具体、可执行
3. **可验证**——每个阶段必须有验证标准
4. **资源丰富**——推荐多种学习资源

## Refusals

- 「这个技能太难了，学不会」 → 鼓励。分解成小步骤，逐步攻克
- 「没时间学」 → 建议。至少了解基础概念

## Integration

- 上游：`/resume-jd` 提供技能缺口
- 下游：`/resume-profile` 更新技能树
- 下游：`/resume-build` 更新简历
- 更新：`.resume-state.json` 的 `pending_learning`
