---
name: resume-optimize
description: 迭代优化简历内容。触发词："优化一下简历"/"改改简历"/"简历优化"。
argument-hint: [jd-id]
allowed-tools: Read, Write, Edit, Glob
---

# /resume-optimize — 简历优化

迭代优化简历内容。让简历更完美。

## Overview

```
[用户：优化一下简历]
  ↓
[Phase 0: 读取当前简历]
  ↓
[Phase 1: 分析优化点]
  ↓
[Phase 2: 执行优化]
  ↓
[Phase 3: 输出结果]
```

## Inputs

| 必填 | 来源 |
|---|---|
| 当前简历 | `resumes/jd-<NNN>-<short>/resume.html` |
| JD 分析 | `resumes/jd-<NNN>-<short>/jd-analysis.md` |

## Workflow

### Phase 0: 读取当前简历

1. 读取 `.resume-state.json` → 获取 `active_jd_id`
2. 读取 `resumes/jd-<NNN>-<short>/resume.html`
3. 读取 `resumes/jd-<NNN>-<short>/jd-analysis.md`

### Phase 1: 分析优化点

```markdown
## 优化分析

### 关键词优化
- JD 关键词：Python, Django, MySQL, Redis, 分布式, 微服务
- 简历覆盖：Python ✅, Django ✅, MySQL ✅, Redis ✅, 分布式 ⚠️, 微服务 ❌
- 建议：补充"微服务"关键词

### 量化优化
- 当前：性能提升 50%
- 建议：可以更具体，如"响应时间从 500ms 降到 250ms"

### STAR 优化
- 当前：缺少 Situation 和 Task
- 建议：补充项目背景和个人职责

### 排版优化
- 当前：排版清晰
- 建议：无需调整

### 长度优化
- 当前：2 页
- 建议：控制在 1-2 页
```

### Phase 2: 执行优化

根据分析执行优化：

1. **关键词优化**
   - 在技能清单中补充"微服务"
   - 在项目描述中突出"分布式"经验

2. **量化优化**
   - "性能提升 50%" → "响应时间从 500ms 降到 250ms，性能提升 50%"

3. **STAR 优化**
   - 补充项目背景：XX 系统是公司的核心业务系统
   - 补充个人职责：负责性能优化模块

4. **排版优化**
   - 无需调整

5. **长度优化**
   - 删除不相关的项目
   - 精简描述

### Phase 3: 输出结果

```
✅ 简历已优化：resumes/jd-001-xx公司后端/resume.html

📊 优化内容：
- 关键词：补充"微服务"
- 量化：补充具体数据
- STAR：补充背景和职责
- 长度：控制在 1.5 页

📁 文件：
- resumes/jd-001-xx公司后端/resume.html
- resumes/jd-001-xx公司后端/resume-v2.html（历史版本）

💡 下一步：
- 导出 PDF？→ "导出 PDF"
- 转换英文简历？→ "本地化"
- 准备面试？→ "准备面试"
- 继续优化？→ "优化一下简历"
```

## Key Rules

1. **针对性**——优化必须针对特定 JD
2. **真实性**——不能为了优化而虚构内容
3. **版本管理**——每次优化创建新版本
4. **原子写**——所有文件使用 .tmp → rename

## Refusals

- 「把这个技能写成精通」 → 拒绝。如实标注
- 「编造一个项目」 → 拒绝。只写有证据支撑的内容

## Integration

- 上游：`/resume-build` 生成初始简历
- 上游：`/resume-jd` 提供 JD 分析
- 下游：`/resume-localize` 中英文本地化
- 下游：`/resume-export` 导出 PDF
- 下游：`/resume-interview` 准备面试
