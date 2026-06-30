---
name: resume-build
description: 根据经历和 JD，生成针对性简历。触发词："针对这个 JD 优化简历"/"生成简历"/"写简历"。
argument-hint: [jd-id]
allowed-tools: Read, Write, Edit, Glob, Bash
---

# /resume-build — 简历生成

根据经历和 JD，生成针对性简历。不是一份简历投天下，是每个 JD 一份定制简历。

## Overview

```
[用户：针对这个 JD 优化简历]
  ↓
[Phase 0: 读取 JD 分析 + self-profile]
  ↓
[Phase 1: 选择模板]
  ↓
[Phase 2: 匹配经历与 JD]
  ↓
[Phase 3: 生成简历内容]
  ↓
[Phase 4: 应用模板]
  ↓
[Phase 5: 输出 HTML]
  ↓
[Phase 6: 用户 review + 调整]
```

## Inputs

| 必填 | 来源 |
|---|---|
| JD 分析 | `resumes/jd-<NNN>-<short>/jd-analysis.md` |
| 技能树 | `profile/self-profile.md` |
| 项目文档 | `profile/projects/*.md` |
| 模板 | `templates/official/*.html` 或 `templates/user/*.html` |

## Workflow

### Phase 0: 读取必要文件

1. 读取 `.resume-state.json` → 获取 `active_jd_id`
2. 读取 `resumes/jd-<NNN>-<short>/jd-analysis.md` → 获取 JD 要求
3. 读取 `profile/self-profile.md` → 获取技能和经历
4. 读取 `profile/projects/*.md` → 获取项目详情

### Phase 1: 选择模板

**优先检查**：`.resume-state.json` 中是否有 `imported_template` 字段。

如果有（用户通过 `/resume-import` 保留了原始模板）：
```
检测到你导入简历时保留了原始模板：
- 模板：templates/imported/my-resume-template.html
- 布局：双栏，主色调 #2c3e50

是否使用这个模板？
a) 是，使用原始模板（推荐）
b) 否，选择其他模板
```

如果用户选择"是"，直接使用 `imported_template` 路径的模板，跳过模板选择。

如果用户选择"否"或没有导入模板，根据目标职位选择模板：

| 职位类型 | 模板 |
|---|---|
| 技术岗 | tech-standard.html / tech-modern.html |
| 产品岗 | product-standard.html |
| 设计岗 | design-creative.html |
| 导入模板 | imported/*.html |
| 用户自定义 | user/*.html |

```
选择简历模板：
a) 技术岗标准模板（推荐）
b) 技术岗现代模板
c) 产品岗标准模板
d) 设计岗创意模板
e) 导入的模板（如有）
f) 自定义模板
```

### Phase 2: 匹配经历与 JD

根据 JD 要求，从你的经历中挑选最相关的：

```markdown
## 匹配策略

### 必须满足的要求
- Python 精通 → 使用 proj-001, proj-003
- MySQL 精通 → 使用 proj-001, proj-003

### 最好满足的要求
- 分布式系统 → 使用 proj-002（部分）

### 加分项
- K8s → 无证据，不写
```

### Phase 3: 生成简历内容

根据匹配结果，生成简历各部分：

**头部**：
- 姓名：从 self-profile.md
- 目标职位：从 JD
- 联系方式：从 self-profile.md

**自我评价**：
- 从 self-profile.md 的个人总结
- 针对 JD 优化关键词

**技能清单**：
- 只写有证据支撑的技能
- 优先写 JD 要求的技能
- 用 JD 的关键词描述技能

**工作经历**：
- 从 self-profile.md 的工作经历
- 突出与 JD 相关的工作内容

**项目经历**：
- 从 profile/projects/*.md
- 只写与 JD 相关的项目
- 用 STAR 法则描述
- 量化成果

**教育背景**：
- 从 self-profile.md

### Phase 4: 应用模板

> **设计决策（v1.3.0）**：模板文件是**布局参考**，实际 HTML 由 Claude 直接生成。
> 不使用 Jinja2 或任何模板渲染引擎。Claude 读取模板的 CSS 风格和 section 结构，直接输出完整 HTML。

1. 读取模板文件 → 提取布局风格（颜色、字体、间距、section 顺序）
2. 基于模板风格，直接生成完整 HTML
3. 确保 HTML 包含所有必要 section（头部、技能、工作经历、项目经历、教育背景）
4. CSS 内联在 `<style>` 标签中，确保 PDF 导出时样式不丢失

### Phase 5: 输出 HTML

1. 创建目录：`resumes/jd-<NNN>-<short>/`
2. 写入文件：`resume.html`
3. 如果已有 `resume.html` → 重命名为 `resume-v<N>.html`
4. 原子写：.tmp → rename

```
✅ 简历已生成：resumes/jd-001-xx公司后端/resume.html

📊 简历内容：
- 技能：8 项（Python, Django, MySQL, Redis, ...）
- 工作经历：2 段
- 项目经历：3 个
- 教育背景：1 段

📁 文件：
- resumes/jd-001-xx公司后端/resume.html
- resumes/jd-001-xx公司后端/resume-v1.html（历史版本）
```

### Phase 6: 用户 review + 调整

```
简历已生成，请 review：

a) 看起来不错，导出 PDF
b) 需要调整某些部分
c) 转换英文简历 / 本地化
d) 重新生成
```

## Key Rules

1. **针对性**——每份简历必须针对特定 JD，不能复用
2. **真实性**——简历内容必须来自 project.md，不能凭空编写
3. **证据链**——每项技能必须有项目支撑
4. **量化**——成果必须量化
5. **原子写**——所有文件使用 .tmp → rename

## Refusals

- 「这个 JD 和之前那个差不多，直接用之前的简历」 → 拒绝。每个 JD 都值得一份定制简历
- 「我没这个项目，但先写上吧」 → 拒绝。只写有证据支撑的内容

## Integration

- 上游：`/resume-jd` 提供 JD 分析
- 上游：`/resume-mine` 提供项目和技能
- 上游：`/resume-import` 可能提供导入的模板（`imported_template` 字段）
- 下游：`/resume-optimize` 优化简历
- 下游：`/resume-localize` 中英文本地化
- 下游：`/resume-export` 导出 PDF
- 下游：`/resume-interview` 准备面试
- 更新：`.resume-state.json` 的 `resume_count` 和 `last_resume_at`
