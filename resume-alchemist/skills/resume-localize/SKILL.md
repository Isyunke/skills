---
name: resume-localize
description: 中英文简历本地化转换，根据目标国家职场文化和企业文化针对性优化内容和排版。触发词："转换英文简历"/"本地化简历"/"中英文转换"/"英文版"/"中文版"。
argument-hint: [--target en|zh] [--company <company-name>]
allowed-tools: Read, Write, Edit, Glob, Bash, AskUserQuestion
---

# /resume-localize — 简历本地化

把你的简历转换为目标语言版本，不是死板翻译，而是根据目标市场职场文化**重新打磨**。

## 为什么不是翻译？

中英文简历的差异不只是语言：

| 维度 | 中文简历 | 英文简历 |
|---|---|---|
| 照片 | 常见 | 不放（反歧视） |
| 个人信息 | 年龄、性别、政治面貌 | 只放联系方式 |
| 自我评价 | 较长，3-5 句 | Professional Summary，1-2 句 |
| 工作描述 | 职责导向 | Action verb + 量化成果 |
| 日期格式 | 2024.01 - 2024.06 | Jan 2024 - Jun 2024 |
| 排版 | 信息密度高 | 留白多，简洁 |
| 关键词 | 中文术语 | 英文术语 |

**逐句翻译 = 简历灾难**。我们需要的是**文化适配**。

---

## Overview

```
[用户：转换英文简历 / build/optimize 后选择本地化]
  ↓
[Phase 0: 读取当前简历]
  ↓
[Phase 1: 确定目标市场]
  ├─ 有意向企业 → 分析企业国家 + 文化
  └─ 无意向企业 → 选择通用目标市场
  ↓
[Phase 2: 文化适配分析]
  ├─ 内容适配策略
  ├─ 格式适配策略
  └─ 关键词适配策略
  ↓
[Phase 3: 内容改写]
  ├─ 自我评价改写
  ├─ 工作经历改写
  ├─ 项目经历改写
  └─ 技能术语转换
  ↓
[Phase 4: 应用目标市场模板]
  ↓
[Phase 5: 输出本地化简历]
  ↓
[Phase 6: 用户 review]
```

## Constants

- **TARGET_MARKETS = {"en-US", "en-UK", "zh-CN", "zh-TW", "ja-JP"}** — 支持的目标市场
- **DEFAULT_TARGET = "en-US"** — 中文简历默认转换为美式英文
- **COMPANY_PROFILES** — 知名企业文化特征库（见附录）

## Inputs

| 必填 | 来源 |
|---|---|
| 当前简历 | `resumes/jd-<NNN>-<short>/resume.html` |
| JD 分析（可选） | `resumes/jd-<NNN>-<short>/jd-analysis.md` |
| self-profile | `profile/self-profile.md` |

## Workflow

### Phase 0: 读取当前简历

1. 读取 `.resume-state.json` → 获取 `active_jd_id`
2. 读取 `resumes/jd-<NNN>-<short>/resume.html` → 获取当前简历内容
3. 如果没有 `active_jd_id` → 询问用户选择哪个简历
4. 检测当前简历语言（中文/英文）

### Phase 1: 确定目标市场

**询问用户**：

```
你有意向企业吗？

a) 有，我有具体的目标企业
b) 没有，使用通用目标市场
```

#### 1a. 有意向企业

```
请输入意向企业名称（如 Google、字节跳动）：
> _
```

根据企业名称：
1. 识别企业所属国家/地区
2. 查询企业文化特征（如有）
3. 确定目标市场（如 `en-US`）

**企业文化分析**：
```
📊 企业分析：Google
- 国家：美国
- 目标市场：en-US
- 文化特征：
  - 重视 "Googleyness"（协作、好奇心）
  - 偏好简洁、数据驱动的描述
  - 技术岗强调系统设计能力
  - 项目描述用 STAR 法则
- 简历调整建议：
  - 强调影响力和可量化成果
  - 使用 "Led", "Built", "Scaled" 等强动词
  - 突出大规模系统经验
```

#### 1b. 无意向企业

```
请选择目标市场：
a) 美国 (en-US) — 简洁、数据驱动、Action verbs
b) 英国 (en-UK) — 稍正式、Cover letter 常见
c) 中国大陆 (zh-CN) — 详细、个人信息全
d) 日本 (ja-JP) — 履歴書格式、高度结构化
```

### Phase 2: 文化适配分析

根据目标市场，生成适配策略：

```markdown
## 本地化策略

### 目标市场：en-US (Google)

#### 内容适配
- 自我评价：3 句 → 1 句 Professional Summary
- 工作描述：职责导向 → 成果导向
  - "负责用户系统开发" → "Led development of user system serving 10M+ users"
  - "参与微服务架构改造" → "Architected microservices migration reducing latency by 60%"
- 项目描述：添加业务背景和技术选型原因
- 技能：中文术语 → 英文术语（精通→Expert, 熟练→Proficient, 了解→Familiar）

#### 格式适配
- 移除：照片、年龄、性别、政治面貌
- 日期格式：2024.01 → Jan 2024
- 联系方式：只保留 email + phone（去掉📍地址，可选加 LinkedIn/GitHub）
- 排版：增加留白，控制在 1 页（应届）或 2 页（资深）

#### 关键词适配
- "分布式系统" → "Distributed Systems"
- "高并发" → "High Concurrency / High Throughput"
- "性能优化" → "Performance Optimization"
- "微服务" → "Microservices"
```

### Phase 3: 内容改写

**核心原则：不是翻译，是改写。**

#### 3.1 自我评价改写

**中文原版**：
> 5 年后端开发经验，专注于高性能、高可用系统设计和开发。擅长 Python 技术栈，熟悉分布式系统和微服务架构。有丰富的性能优化经验，曾主导多个核心系统的性能优化项目。

**英文改写（美式）**：
> Senior Backend Engineer with 5 years of experience building high-performance, distributed systems. Proven track record in scaling Python-based platforms to handle millions of requests, with deep expertise in microservices architecture and performance optimization.

**改写规则**：
- 开头用 "Senior [Role] with X years of experience..."
- 用 "Proven track record in..." 替代 "有丰富的...经验"
- 量化！"多个核心系统" → "platforms serving millions of requests"
- 不要用 "I" 开头（英文简历惯例）

#### 3.2 工作经历改写

**中文原版**：
> 负责核心电商系统的架构设计和开发
> 主导性能优化项目，提升系统性能 70%

**英文改写**：
> Architected and developed core e-commerce platform processing 100K+ daily orders
> Led performance optimization initiative, reducing page load time from 500ms to 150ms (70% improvement)

**改写规则**：
- 每条以强动词开头：Led, Built, Architected, Scaled, Optimized, Designed
- 量化一切：数字、百分比、规模
- 用过去时（即使还在职，除非是当前工作的当前职责）
- 避免 "Responsible for..."（弱动词）

#### 3.3 项目经历改写

**中文原版**：
> XX 电商平台是公司的核心业务系统，日活用户 100w+，日订单量 10w+。随着业务增长，系统性能逐渐下降。

**英文改写**：
> Core e-commerce platform serving 1M+ daily active users and processing 100K+ orders. Addressed critical performance degradation caused by rapid business growth.

**改写规则**：
- 第一句：项目规模和业务价值
- 第二句：你解决的核心问题
- 后续：你的具体工作（用 STAR 法则）
- 结尾：量化成果

#### 3.4 技能术语转换

| 中文 | 英文 |
|---|---|
| 精通 | Expert |
| 熟练 | Proficient |
| 了解 | Familiar |
| 分布式系统 | Distributed Systems |
| 高并发 | High Concurrency |
| 性能优化 | Performance Optimization |
| 微服务架构 | Microservices Architecture |
| 消息队列 | Message Queue |
| 负载均衡 | Load Balancing |
| 缓存 | Caching |

### Phase 4: 应用目标市场模板

根据目标市场选择模板：

| 目标市场 | 模板 | 说明 |
|---|---|---|
| en-US | tech-standard-en.html | 美式简洁风格 |
| en-UK | tech-standard-en.html | 同美式，稍正式 |
| zh-CN | tech-standard.html | 中文标准模板 |
| ja-JP | 待开发 | 日式履歴書格式 |

**模板差异**：
- 英文模板：无照片区域、无个人信息区域、更大字体、更多留白
- 中文模板：有照片区域、有个人信息区域、信息密度高

### Phase 5: 输出本地化简历

**命名规则**：

| 场景 | 文件名 | 说明 |
|---|---|---|
| 中→英（通用） | `resume-en.html` | 通用英文版 |
| 中→英（特定企业） | `resume-en-google.html` | 针对 Google 的英文版 |
| 英→中（通用） | `resume-zh.html` | 通用中文版 |
| 英→中（特定企业） | `resume-zh-bytedance.html` | 针对字节跳动的中文版 |
| 历史版本 | `resume-en-v1.html` | 版本号递增 |

**输出**：
```
✅ 简历本地化完成

📊 转换详情：
- 源语言：中文 (zh-CN)
- 目标语言：英文 (en-US)
- 目标企业：Google
- 内容改写：12 处
- 格式调整：移除照片/个人信息，调整日期格式

📁 文件：
- resumes/jd-001-xx公司后端/resume-en-google.html
- resumes/jd-001-xx公司后端/resume-en.html（通用英文版，同步更新）

💡 下一步：
- 导出 PDF？→ "导出 PDF"
- 准备英文面试？→ "准备面试"
- 继续优化？→ "优化一下简历"
```

### Phase 6: 用户 review

```
本地化简历已生成，请 review：

a) 看起来不错，导出 PDF
b) 需要调整某些部分（告诉我哪里需要改）
c) 针对其他企业重新生成
d) 回到中文版本
```

## Key Rules

1. **改写不是翻译**——逐句翻译 = 简历灾难。用目标市场的表达习惯重新打磨
2. **文化适配**——不同国家的简历规范差异巨大，必须尊重
3. **真实性不变**——三原则依然适用，改写不能夸大或虚构
4. **量化优先**——英文简历尤其强调可量化的成果
5. **原子写**——所有文件使用 .tmp → rename
6. **双版本维护**——本地化后保留原始版本，两个版本独立管理

## Refusals

- 「直接翻译就行，不用改格式」 → 拒绝。文化适配是本功能的核心价值
- 「把中文简历的个人信息也放英文版」 → 拒绝。英文简历不放照片/年龄/性别
- 「英文版写得更好听一点」 → 拒绝。如实描述，不能夸大
- 「跳过 review，直接用」 → 建议 review。本地化后的简历更需要检查准确性

## Integration

- 上游：`/resume-build` 生成初始简历
- 上游：`/resume-optimize` 优化简历
- 上游：`/resume-jd` 提供 JD 分析（用于关键词适配）
- 下游：`/resume-export` 导出 PDF（支持本地化版本）
- 下游：`/resume-interview` 准备面试（可切换语言）
- 更新：`.resume-state.json`（可选）

---

## 附录：企业文化特征库

### 美国科技公司

| 公司 | 文化关键词 | 简历偏好 |
|---|---|---|
| Google | Googleyness, impact, scale | 强调影响力和规模，简洁数据驱动 |
| Meta | Move fast, impact | 强调速度和影响力，偏好创业者心态 |
| Amazon | Leadership Principles | 每条经历对应一个 LP，强调 customer obsession |
| Apple | Secrecy, excellence | 强调产品质量和用户体验 |
| Microsoft | Growth mindset | 强调学习能力和协作 |

### 中国科技公司

| 公司 | 文化关键词 | 简历偏好 |
|---|---|---|
| 字节跳动 | Always Day 1, 扁平化 | 强调创新和自驱力 |
| 阿里 | 文化契合, 价值观 | 强调团队协作和业务理解 |
| 腾讯 | 产品思维, 用户体验 | 强调产品感和技术深度 |
| 美团 | 长期主义, 基础设施 | 强调系统性和稳定性 |

### 通用英文简历强动词表

**Leadership**: Led, Directed, Managed, Oversaw, Coordinated
**Achievement**: Achieved, Delivered, Exceeded, Improved, Reduced
**Creation**: Built, Designed, Architected, Developed, Implemented
**Optimization**: Optimized, Streamlined, Automated, Enhanced, Refactored
**Scale**: Scaled, Expanded, Grew, Increased, Amplified
