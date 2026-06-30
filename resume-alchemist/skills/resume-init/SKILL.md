---
name: resume-init
description: 简历炼金术士的首次 onboarding 与脚手架创建器。触发词："初始化"/"init"/"首次使用"/"setup"。**必须在用户第一次会话执行；其他子 skill 在 .resume-state.json 不存在时自动路由到此。**
argument-hint: [— role: tech|product|design|other]
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /resume-init — 首次 onboarding

让用户从零到能开始炼金，全程 ≤ 5 分钟。

## Overview

```
[用户首次说"初始化"]
  ↓
[Phase 0: 检测当前状态]
  ↓
[Phase 1: 首屏文案 — 适用性 + 期望管理]
  ↓
[Phase 2: 4 个问题（一问一答）]
  ↓
[Phase 3: 创建脚手架]
  ↓
[Phase 4: 生成初始简历模板]
  ↓
[Phase 5: 给"下一步该说什么"清单]
```

## Constants

- **DEFAULT_EXPERIENCE_LEVEL = "应届"**
- **DEFAULT_INDUSTRY = "互联网"**

> 💡 调用时覆盖：`/resume-init — role: tech`

## Inputs

无。所有信息从 4 个对话问题里收集。

## Workflow

### Phase 0: 检测当前状态

1. 读用户当前工作目录
2. 检查是否已存在 `.resume-state.json`：
   - 存在 → 提示"项目似乎已初始化（state file 存在）。要重新初始化会覆盖现有配置——确认？" 等用户明确确认才继续
   - 不存在 → 进入 Phase 1

### Phase 1: 首屏直白告知期望

向用户输出：

```
🧪 简历炼金术士 / Resume Alchemist

把你的经历炼成黄金，把 JD 炼成 offer。

接下来 3-5 分钟我会问你 4 个问题搞清楚你的目标。
两件事先说在前面：

1. **简历内容必须真实**——我会引导你挖掘真实经历，不会帮你编造
2. **每份简历都针对特定 JD**——不是一份简历投天下

准备好开始吗？
```

### Phase 2: 4 个问题（一问一答）

**Q1: 目标职位**

> "你想从事什么职位？
> a) **技术岗**（后端/前端/全栈/算法/...）
> b) **产品岗**（产品经理/产品运营/...）
> c) **设计岗**（UI/UX/平面/...）
> d) **其他**（市场/销售/人力/...）"

记录到 `target_role`。

**Q2: 目标行业**

> "你目标什么行业？
> a) **互联网**（大厂/创业公司/...）
> b) **金融**（银行/证券/基金/...）
> c) **教育**（K12/高等教育/在线教育/...）
> d) **其他**（医疗/制造/零售/...）"

记录到 `target_industry`。

**Q3: 经验水平**

> "你有多少年工作经验？
> a) **应届**（在校/刚毕业）
> b) **1-3年**
> c) **3-5年**
> d) **5年+**"

记录到 `experience_level`。

**Q4: 现有材料**

> "你有什么现成的简历或项目文档吗？
> a) **有简历**（我帮你导入）
> b) **有项目文档**（我帮你整理）
> c) **什么都没有**（我们从零开始）
> d) **有 JD**（我先分析这个 JD）"

根据回答决定下一步：
- a) 提示用户提供简历文件 → 导入
- b) 提示用户提供项目文档 → 导入
- c) 直接进入 Phase 3
- d) 提示用户提供 JD → 先分析 JD

### Phase 3: 创建脚手架

按顺序创建并**解释每一项的作用**：

1. **`.resume-state.json`**
   ```
   "正在创建 .resume-state.json — 各子 skill 共享上下文的地方。
    这次 init 收集的所有答案都会写在这里。"
   ```
   写入：
   ```json
   {
     "schema_version": "1.0",
     "skill_version": "1.0.0",
     "target_role": "<Q1 答案>",
     "target_industry": "<Q2 答案>",
     "experience_level": "<Q3 答案>",
     "project_count": 0,
     "skill_count": 0,
     "jd_count": 0,
     "resume_count": 0,
     "last_mine_at": null,
     "last_jd_at": null,
     "last_resume_at": null,
     "last_interview_at": null,
     "active_jd_id": null,
     "pending_learning": [],
     "initialized_at": "<本地 ISO 8601 含时区>"
   }
   ```

2. **`profile/self-profile.md`**
   ```
   "正在创建 profile/self-profile.md — 你的技能树和个人档案。
    后续深挖经历会不断更新这个文件。"
   ```
   - 从 `templates/` 复制模板
   - 填入基本信息（从 Q1-Q3 派生）

3. **`profile/projects/`** + **`profile/work-history/`**
   ```
   "正在创建项目和工作经历目录。
    后续深挖经历会在这里创建具体的文档。"
   ```

4. **`resumes/`**
   ```
   "正在创建简历存档目录。
    每次针对 JD 优化简历都会在这里创建子目录。"
   ```

5. **`learning/`**
   ```
   "正在创建学习区目录。
    后续发现技能缺口会在这里创建学习计划。"
   ```

6. **`templates/`**
   ```
   "正在创建用户自定义模板目录。
    你可以在这里添加自己的简历模板。"
   ```

### Phase 4: 生成初始简历模板

根据 Q1（目标职位）生成对应的简历模板：

| Q1 | 模板 |
|---|---|
| a) 技术岗 | tech-standard.html |
| b) 产品岗 | product-standard.html |
| c) 设计岗 | design-creative.html |
| d) 其他 | tech-standard.html（默认） |

```
"正在生成初始简历模板。
 这是基于你的目标职位生成的模板，后续会根据具体 JD 优化。"
```

### Phase 5: 给"下一步该说什么"清单

```
✅ 初始化完成（目标：[职位] / [行业] / [经验]）

下次你可以直接说这些：

📝 深挖经历    → "聊聊我的经历"
📋 分析 JD     → "分析这个 JD [粘贴 JD]"
📄 生成简历    → "针对这个 JD 优化简历"
🎤 面试准备    → "准备面试"
📚 学习指导    → "这个技能我不会"
📊 看状态      → "状态"

💡 建议先深挖经历，再分析 JD。
   没有真实经历，再好的简历也是空中楼阁。

现在想：
a) 深挖一下你的经历？
b) 分析一个 JD？
c) 先看看状态？
```

## Key Rules

1. **不假装成功**：任何步骤失败 → 明确告诉用户哪一步出错
2. **不批量提问**：4 个问题一次问一个
3. **不静默 mkdir**：每创建一个文件都解释它的作用
4. **state 字段统一**：所有 enum 值从问题答案映射，不是直接存字母

## Refusals

- 「跳过 Q1-Q4，直接给我创建所有文件」 → 拒绝。问题答案直接影响默认配置
- 「我已经在别处初始化过了，把那个项目的配置同步过来」 → 慎重。提示用户手动 cp

## Integration

- 写完后，主 SKILL.md 的路由就解锁了所有其他子 skill
- `/resume-mine` 读 `profile/self-profile.md` 开始深挖
- `/resume-jd` 读 `.resume-state.json` 的 `target_role` 决定分析重点
