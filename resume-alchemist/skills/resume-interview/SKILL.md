---
name: resume-interview
description: 根据简历和 JD，生成面试题库和回答策略。触发词："准备面试"/"模拟面试"/"面试指导"。
argument-hint: [jd-id]
allowed-tools: Read, Write, Edit, Glob
---

# /resume-interview — 面试准备

根据简历和 JD，生成面试题库和回答策略。让你面试时胸有成竹。

## Overview

```
[用户：准备面试]
  ↓
[Phase 0: 读取简历 + JD 分析]
  ↓
[Phase 1: 生成自我介绍]
  ↓
[Phase 2: 生成项目深挖问题]
  ↓
[Phase 3: 生成技术问题]
  ↓
[Phase 4: 生成行为问题]
  ↓
[Phase 5: 生成反问环节]
  ↓
[Phase 6: 输出面试指导]
```

## Inputs

| 必填 | 来源 |
|---|---|
| 简历 | `resumes/jd-<NNN>-<short>/resume.html` |
| JD 分析 | `resumes/jd-<NNN>-<short>/jd-analysis.md` |
| 项目文档 | `profile/projects/*.md` |

## Workflow

### Phase 0: 读取必要文件

1. 读取 `.resume-state.json` → 获取 `active_jd_id`
2. 读取 `resumes/jd-<NNN>-<short>/resume.html` → 获取简历内容
3. 读取 `resumes/jd-<NNN>-<short>/jd-analysis.md` → 获取 JD 要求
4. 读取 `profile/projects/*.md` → 获取项目详情

### Phase 1: 生成自我介绍

根据简历生成 1 分钟版自我介绍：

```markdown
## 自我介绍（1分钟版）

"面试官您好，我叫 XX，XX 年工作经验，专注于后端开发。
最近的项目是 XX，负责 XX 模块，使用 Python + Django 开发，
性能提升了 50%，用户量增长了 100%。
我对贵公司的 XX 岗位很感兴趣，我的 XX 经验与岗位要求非常匹配。"
```

**自我介绍要点**：
- 简洁明了：1 分钟内
- 突出亮点：与 JD 最相关的经验
- 量化成果：用数据说话
- 表达兴趣：对岗位的热情

### Phase 2: 生成项目深挖问题

根据简历中的项目经历，生成必问问题：

```markdown
## 项目深挖（必问）

### Q1: 介绍一下你最有挑战的项目

**STAR 回答**：

- **Situation**: 项目背景是什么？
  - "XX 系统是公司的核心业务系统，日活用户 100w+"

- **Task**: 你的任务是什么？
  - "我负责性能优化模块，目标是将响应时间从 500ms 降到 200ms"

- **Action**: 你做了什么？
  - "1. 分析瓶颈，发现是数据库查询慢
    2. 优化 SQL，添加索引
    3. 引入 Redis 缓存
    4. 优化代码逻辑"

- **Result**: 结果如何？
  - "响应时间从 500ms 降到 150ms，性能提升 70%"
```

**项目深挖要点**：
- 用 STAR 法则
- 量化成果
- 突出个人贡献
- 准备追问回答

### Phase 3: 生成技术问题

根据 JD 要求，生成技术问题：

```markdown
## 技术问题（根据 JD）

### 分布式系统

**Q: 什么是分布式系统？**

**回答要点**：
- 定义：多个独立计算机协作完成任务
- 优势：可扩展、高可用
- 挑战：一致性、网络分区

**Q: CAP 理论是什么？**

**回答要点**：
- C (Consistency): 一致性
- A (Availability): 可用性
- P (Partition tolerance): 分区容错
- 三者只能满足其二
```

**技术问题要点**：
- 覆盖 JD 核心要求
- 从基础到深入
- 准备实际案例
- 准备追问回答

### Phase 4: 生成行为问题

根据简历和 JD，生成行为问题：

```markdown
## 行为问题

### Q: 你如何处理团队冲突？

**STAR 回答**：

- **Situation**: 冲突背景
- **Task**: 需要解决什么
- **Action**: 你怎么处理的
- **Result**: 结果如何

### Q: 你如何管理项目进度？

**STAR 回答**：

- **Situation**: 项目背景
- **Task**: 需要完成什么
- **Action**: 你怎么管理的
- **Result**: 结果如何
```

**行为问题要点**：
- 用 STAR 法则
- 突出软技能
- 准备具体案例
- 准备追问回答

### Phase 5: 生成反问环节

```markdown
## 反问环节

### 推荐问题

1. **关于职位**
   - 这个职位的日常工作是什么？
   - 这个职位最大的挑战是什么？
   - 这个职位的晋升路径是什么？

2. **关于团队**
   - 团队的技术栈是什么？
   - 团队的开发流程是什么？
   - 团队的规模和组成？

3. **关于公司**
   - 公司对这个职位的期望是什么？
   - 公司的技术发展方向？
   - 公司的文化和价值观？

### 避免的问题

- ❌ 薪资福利（初面不要问）
- ❌ 加班情况（显得不积极）
- ❌ 什么都能搜到的问题
```

### Phase 6: 输出面试指导

创建文件：`resumes/jd-<NNN>-<short>/interview-guide.md`

```
✅ 面试指导已生成：resumes/jd-001-xx公司后端/interview-guide.md

📋 内容：
- 自我介绍（1分钟版）
- 项目深挖问题（3 个）
- 技术问题（5 个）
- 行为问题（3 个）
- 反问环节（3 类）

📁 文件：
- resumes/jd-001-xx公司后端/interview-guide.md
```

## Key Rules

1. **针对性**——面试指导必须针对特定 JD 和简历
2. **STAR 法则**——所有回答都要用 STAR 法则
3. **量化**——成果必须量化
4. **完整性**——覆盖自我介绍、项目深挖、技术问题、行为问题、反问环节

## Refusals

- 「随便准备一下就行」 → 建议。充分准备是面试成功的关键
- 「我没时间准备，直接面」 → 建议。至少准备自我介绍和项目深挖

## Integration

- 上游：`/resume-build` 提供简历
- 上游：`/resume-jd` 提供 JD 分析
- 上游：`/resume-mine` 提供项目详情
- 更新：`.resume-state.json` 的 `last_interview_at`
