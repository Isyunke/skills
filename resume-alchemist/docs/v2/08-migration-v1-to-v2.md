# 08 · v1 → v2 迁移规范

> 用户的承诺：**完全向后兼容**。
> v1 用户跑一次 `resume migrate` 就能用 v2，所有历史数据保留，触发词不变，工作流不变。
> 这一章定义"无缝"的具体含义和实现细节。

---

## 一、兼容性承诺等级

| 维度 | 承诺 | 实现 |
|---|---|---|
| 数据 | 🔒 **100% 不丢失** | 自动备份到 `.resume-backup-v1/` + 转换到 v2 schema |
| 触发词 | 🔒 **100% 保留** | v2 orchestrator 含 v1 全部触发词的别名映射 |
| 工作流 | 🔒 **100% 兼容** | 5 阶段闭环不变（深挖 → JD → 简历 → 面试 → 学习） |
| 文件路径 | 🟡 **路径调整但仍可读** | 老 `proj-001.md` → 新 `proj-001-xxx/data.yaml + narrative.md`；`migrate` 自动转 |
| Claude Code 体验 | 🔒 **不退化** | SKILL.md 重组但触发词不变；新增 MCP 是可选项 |
| hooks 行为 | 🟢 **升级为更强校验** | bash hooks 废弃，由 `evidence_validator.py` 取代，更严但更友好 |
| schema_version | 🔒 **migrate 跨版本** | 1.0 → 2.0 自动；未来 2.x → 2.y 同样自动 |

---

## 二、迁移流程（用户视角）

### 2.1 准备阶段

```bash
# 1. 升级 Python 包
pip install --upgrade resume-alchemist
# 现在装的是 v2.0.0+

# 2. 检测当前项目状态
cd <your-resume-project>
resume migrate --dry-run
```

`--dry-run` 输出预览：

```
🔍 Migration plan: v1.3.0 → v2.0.0

Detected v1 schema_version: 1.0

数据迁移:
  ✓ 5 个项目 → 5 个目录式 data.yaml + narrative.md
  ✓ self-profile.md → identity.yaml + skills/data.yaml + self-profile/data.yaml
  ✓ 3 个 JD 分析 → 3 个 jd.yaml + match-report.yaml
  ✓ 5 份简历 → 5 个 resume-v*.yaml + 保留原 HTML

新增（用户首次见到）:
  + outcomes.yaml 模板（每个 jd-* 目录）
  + .resume-config.yaml
  + .resume-cache/ 目录

废弃（移走但保留备份）:
  ⚠ truth-verification.sh / evidence-chain.sh → 备份到 .resume-backup-v1/hooks/
    （由 evidence_validator.py 取代）

备份:
  📦 全部 v1 原始数据 → .resume-backup-v1/
     可随时跑 `resume migrate --revert` 回滚

预估耗时: ~10 秒（不调 LLM）

继续? (y/n)
```

### 2.2 执行阶段

```bash
resume migrate
```

输出：

```
🚀 Migrating v1.3.0 → v2.0.0

[1/7] Backup v1 data...                            ✅ .resume-backup-v1/
[2/7] Convert profile/self-profile.md...           ✅ identity + skills + self-profile
[3/7] Convert 5 projects to v2 directory format... ✅ proj-001..proj-005
[4/7] Convert 3 JD analyses...                     ✅ jd.yaml + match-report.yaml
[5/7] Convert 5 resumes to data + render...        ✅ resume-v*.yaml (HTML 保留)
[6/7] Generate outcomes.yaml templates...          ✅ 3 个
[7/7] Build initial .resume-state.json...          ✅

🔎 Running validator on migrated data...
  ✓ truth_first:    passed
  ⚠ evidence_chain: 1 warning（skill: K8s, proj-002 无量化）
  ✓ targeted_for_jd: passed

⚠️ 1 warning。这些是 v2 新增的校验，v1 时没卡。
   要立刻修复吗？(y/skip)
用户: skip

✅ 迁移完成。

下一步建议:
  → resume status     看看新版 dashboard
  → resume profile show skills    检查技能树是否需要补证据
  → 启动 MCP server: resume serve   让 Cursor/ChatGPT 也能用
```

### 2.3 老用户日常体验（迁移后）

```
用户(在 Claude Code 里): 聊聊我的经历

# 完全和 v1 一样的对话体验
agent: 好的，先从最近的开始？这个项目背景是什么？
...
```

**触发词、对话节奏、输出结构** 都和 v1 一致。唯一的差别：

- 写入的不是 `proj-001-xxx.md`，而是 `proj-001-xxx/data.yaml`（用户感知不到，除非他打开文件夹看）
- 校验从"警告"变"阻断"（v2 evidence_validator 更严）

---

## 三、数据迁移规则（详细）

### 3.1 `.resume-state.json` 字段映射

| v1 字段 | v2 处理 |
|---|---|
| `schema_version: "1.0"` | → `"2.0"` |
| `skill_version: "1.0.0"` | → `"2.0.0"` |
| `target_role` | → `identity.yaml.target.role` |
| `target_industry` | → `identity.yaml.target.industry` |
| `experience_level: "3-5年"` | → `identity.yaml.target.experience_level: "3-5y"` (enum 归一) |
| `project_count` etc. | 派生重算（不再持久化） |
| `last_*_at` | 派生重算 |
| `active_jd_id` | 保留到 state cache |
| `pending_learning: []` | → `learning/*/plan.yaml` 中 |
| `imported_template` | → `templates/user/` 下保留；新简历的 `resume.yaml.template` 引用之 |
| `initialized_at` | 写入 `identity.yaml.created_at` |

### 3.2 `profile/self-profile.md` 拆分

v1 单文件 → v2 三个文件：

| v1 区块 | v2 去向 |
|---|---|
| 基本信息（姓名、目标、教育） | `profile/identity.yaml` |
| 个人总结 | `profile/self-profile/data.yaml.summary` |
| 技能树（编程语言/框架/数据库/工具/软技能） | `profile/skills/data.yaml.categories[]` |
| 工作经历 | `profile/work-history/<id>/data.yaml` |
| 项目经历表格 | 已存在于 `profile/projects/*.md`，归并 |
| 证书/荣誉 | `profile/self-profile/data.yaml.certifications[]` |
| 自我评价 | 同 `summary`（去重） |

### 3.3 `profile/projects/proj-001.md` 升级

v1: 单 markdown 文件
v2: 目录 + data.yaml + narrative.md

迁移步骤：

```python
def migrate_project(v1_md_path: Path) -> Path:
    # 1. 解析 v1 markdown
    parsed = parse_v1_project_md(v1_md_path)  # 内置 schema 解析器

    # 2. 转换为 v2 schema
    project = Project(
        schema_version="2.0",
        id=parsed.id,
        verified_by="dialog",   # 默认（v1 没记录就当对话深挖）
        meta=...,
        star=...,
        tech_stack=...,
        achievements=parsed.results_as_achievements,
        ...
    )

    # 3. 创建目录
    new_dir = v1_md_path.parent / parsed.id_short
    new_dir.mkdir()

    # 4. 写 data.yaml
    atomic_write_yaml(new_dir / "data.yaml", project.model_dump())

    # 5. 渲染 narrative.md（替换原 md）
    renderer.render_narrative(
        data=project,
        template="templates/narrative/project.md.j2",
        output=new_dir / "narrative.md",
    )

    # 6. 备份原文件
    shutil.move(v1_md_path, BACKUP_DIR / v1_md_path.name)

    return new_dir
```

**关键**：v2 的 `narrative.md` **内容上和 v1 几乎一样**——用户用 Claude Code 读到的项目描述不会有违和感。

### 3.4 `resumes/jd-<NNN>-<short>/` 升级

| v1 文件 | v2 处理 |
|---|---|
| `jd-analysis.md` | 解析回 `jd.yaml`（含原始 JD 文本），重渲染 `jd-analysis.md`；可选生成 `match-report.yaml` |
| `resume.html` | **保留原文件**，并生成对应 `resume-v1.yaml`（反向解析）作为可继续编辑的数据源 |
| `resume.pdf` | 保留 |
| `resume-v<N>.html` | 同样反向解析为 `resume-v<N>.yaml` |
| `interview-guide.md` | 解析为 `interview-guide.yaml`，重渲染 md |
| `outcomes.yaml` | **新增**：空文件模板 |

#### 反向解析 HTML → data.yaml

为了保留历史简历的可编辑性，提供 `tools/reverse_parser.py`：

```python
def reverse_parse_html_to_resume_yaml(html: str, jd: JobDescription) -> Resume:
    """Best-effort: 把 v1 LLM 生成的 HTML 反向解析回 v2 Resume schema。"""
    # 用 BeautifulSoup 提取 section
    # 弱处：text → 结构化字段可能丢一些样式信息
    # 用户被告知这是 best-effort，可在 v2 重生成时获得完整结构
```

**告知用户**：

```
⚠️ 注意：你的 v1 简历是 LLM 直接生成的 HTML，转换为 v2 yaml 是 best-effort。
   原 HTML 保留在原路径，可继续投递。
   下次想用 v2 的 diff/optimize 功能：建议跑一次 `resume output --target resume`
   重新基于结构化数据生成新版本。
```

### 3.5 templates/ 处理

| v1 路径 | v2 处理 |
|---|---|
| `templates/official/*.html` | 保留兼容性别名，但实际改用 `templates/official/<name>/template.html.j2` 形式（详见 [03 §四](03-tools-layer-spec.md)） |
| `templates/user/*.html` | 自动转换为 Jinja2 形式（用 `tools/template_migrator.py`） |
| `templates/imported/*.html` | 保留路径不变，按"用户自定义"对待 |

template 迁移失败时，**降级提示**：

```
⚠️ templates/user/my-template.html 包含 Handlebars 语法 ({{#each}}),
   v2 用 Jinja2 ({% for %}). 我尝试自动转换但有 3 处可能不准。
   选项:
   a) 让我尝试 LLM-assisted 转换（需要 confirm 后才落盘）
   b) 我帮你保留原文件，但下次 build 用官方模板
   c) 我贴出 diff，你手动调整
```

### 3.6 hooks/ 处理

```
hooks/truth-verification.sh    → 移到 .resume-backup-v1/hooks/
hooks/truth-verification.json  → 同上
hooks/evidence-chain.sh        → 同上
hooks/evidence-chain.json      → 同上
```

v2 不再用 bash hook（详见 [03 §二](03-tools-layer-spec.md)）。

用户的 Claude Code `.claude/settings.json` 中的 hook 配置自动**注释化**（不删，加 `enabled: false` 并附注释）：

```jsonc
// 由 resume migrate 自动注释。v2 改用 evidence_validator.py，
// 在 resume build / export 流程内强制执行。原配置保留以便回滚。
"hooks": {
  // "PreToolUse": [...]
}
```

---

## 四、Claude Code 路径的特殊承诺

> 这一节专门回应"是否保留 Claude Code 体验"的问题——答案是：**保留，且不退化**。

### 4.1 `~/.claude/skills/resume-alchemist/` 目录

v2 install.sh 会：

```bash
# 老用户运行 install.sh（v2 版本）
# 1. 检测 ~/.claude/skills/resume-alchemist/ 已存在（v1 安装过）
# 2. 备份原目录到 ~/.claude/skills/resume-alchemist-v1-backup/
# 3. symlink 新的 v2 SKILL.md 集合（13 → 7）
# 4. 显示触发词对照表，让用户知道"你以前说的话现在也都通用"
```

### 4.2 触发词向后兼容（强制）

所有 v1 触发词必须**继续工作**：

```yaml
# orchestrator.yaml — 内置 v1 兼容别名
aliases_from_v1:
  "聊聊我的经历":  intake.dialog
  "深挖一下":     intake.dialog
  "导入简历":     intake.file
  "验证项目":     intake.code
  "代码溯源":     intake.code
  "看看我的技能树": profile.show
  "分析这个 JD":  match
  "针对这个 JD 优化简历": output.resume
  "优化简历":     output.optimize
  "转换英文简历": output.localized
  "准备面试":     output.interview
  "学什么":      output.learning
  "导出 PDF":    output.export
  "状态":        status

  # 包括所有英文别名
  ...
```

加入回归测试：

```python
# tests/compat/test_v1_triggers.py
@pytest.mark.parametrize("trigger", V1_TRIGGERS)
def test_v1_trigger_still_works(trigger):
    result = orchestrator.route(user_input=trigger, state=MOCK_STATE)
    assert result.skill is not None, f"v1 trigger '{trigger}' lost!"
```

### 4.3 Sub-skill SKILL.md 数量减少 ≠ 体验降级

v2 把 13 个 sub-skill 合并到 7 个。但**每个 SKILL.md 的入口（trigger）都齐全**：

```
~/.claude/skills/resume-alchemist/skills/
  init/SKILL.md
  intake/
    SKILL.md              # 主入口，含 mode 切换
    mode-dialog.md        # v1 mine 的内容
    mode-file.md          # v1 import 的内容
    mode-code.md          # v1 verify 的内容
  match/SKILL.md
  output/
    SKILL.md
    target-resume.md      # v1 build
    target-optimize.md
    target-interview.md
    target-learning.md
    target-localized.md
    target-export.md
  profile/SKILL.md
  review/SKILL.md
  status/SKILL.md
  track/SKILL.md           # v2 新增
```

主 SKILL.md 的路由表保留 v1 风格（用户读了一眼能看懂自己以前用过什么）。

### 4.4 MCP 是**附加**不是**替代**

| 老 v1 用户 | 不强制装 MCP，照常用 Claude Code |
| 想跨 agent 用 | 加一条 `resume serve` 启动 MCP server |

`resume migrate` 默认不启用 MCP，**避免吓退老用户**。在迁移最后给提示：

```
✅ 迁移完成。你现在可以像 v1 一样继续用 Claude Code。

🎁 可选新功能（不影响当前用法）:
   - 想在 Cursor/ChatGPT 也用?
     → resume serve --transport stdio   并在 Cursor 配置 MCP
   - 想看反馈 dashboard?
     → 投简历后用 "我投了简历" 触发 track，让 outcomes 积累起来
```

### 4.5 旧 Bash hooks 的过渡

```
v1 hook 行为             v2 替代               兼容性
truth-verification.sh    evidence_validator    更严格，但只在 resume build/export 时跑
evidence-chain.sh        evidence_validator    同上
```

老用户的现成 `.claude/settings.json` 中如果引用了 v1 hook 路径——`resume migrate` 检测到后：

```
检测到 .claude/settings.json 引用了 v1 hooks。
v2 已移除 bash hook，改为流程内校验。

要怎么办？
  a) 注释掉旧配置（推荐，可随时恢复）
  b) 保留旧配置但删掉脚本（hook 会静默失败）
  c) 什么都不动（hook 会报错，但不影响 v2 工作）
```

---

## 五、回滚方案

如果用户对 v2 不满意：

```bash
resume migrate --revert
```

行为：

```
🔄 Revert v2 → v1

[1/4] Verifying .resume-backup-v1/ exists...   ✅
[2/4] Restoring v1 files...                    ✅
[3/4] Removing v2-only files...
       (你的 outcomes.yaml 会被备份到 .resume-backup-v2/)
[4/4] Downgrade trigger...

⚠️ pip 仍是 v2 版本。如果你想完全回到 v1:
   pip install resume-alchemist==1.3.*

✅ Reverted.
```

**回滚不删用户在 v2 期间新增的数据**——例如 outcomes.yaml 会被另存到 `.resume-backup-v2/` 让用户有机会找回。

---

## 六、版本兼容矩阵

| 用户场景 | v1 (1.3.x) | v2.0 |
|---|---|---|
| Claude Code only | ✅ | ✅ |
| MCP（Cursor / Cline 等） | ❌ | ✅ |
| CLI | ⚠️ 限于 hooks | ✅ 完整 |
| Outcomes 跟踪 | ❌ | ✅ |
| 结构化数据校验 | ⚠️ grep | ✅ pydantic |
| JSON Resume 互操作 | ❌ | ✅ |
| 已有项目继续投简历 | ✅ | ✅ |
| 多设备 git 同步 | ✅ markdown | ✅ yaml 更稳 |

---

## 七、迁移失败的处理

每个迁移步骤是原子的、可重入的：

```python
def migrate_step(step_id, fn):
    sentinel = BACKUP_DIR / f".step-{step_id}.done"
    if sentinel.exists():
        log(f"[{step_id}] skipped (already done)")
        return
    try:
        fn()
        sentinel.touch()
    except Exception as e:
        log_error(f"[{step_id}] failed: {e}")
        raise MigrationFailed(step_id, e, recovery_hint=HINTS[step_id])
```

如果中途失败：

```
❌ Migration failed at step 3/7 (convert projects)
   Error: proj-002.md 的 STAR 段缺失，无法解析

恢复选项:
  a) 跳过 proj-002，继续迁移其他（resume migrate --skip-file proj-002.md）
  b) 手动修一下 proj-002.md 的格式，然后 resume migrate --resume
  c) 撤销已迁移的内容（resume migrate --revert）

已完成步骤已记录，下次 resume migrate 会从失败点继续。
```

---

## 八、迁移测试矩阵

```
tests/migration/
  fixtures/
    v1-minimal/          # 只有 init 跑过
    v1-typical/          # 有 3 项目 + 1 JD + 1 简历
    v1-rich/             # 完整用户：5 项目 + 3 JD + 5 简历 + 2 学习计划
    v1-corrupted/        # 故意损坏的数据
    v1-with-user-templates/
    v1-edge-cases/       # 中文文件名、emoji、空 STAR 等

  test_migrate_minimal.py
  test_migrate_typical.py
  test_migrate_rich.py
  test_migrate_corrupted_handling.py
  test_migrate_user_templates.py
  test_revert_after_migrate.py
  test_idempotency.py    # 重复跑 migrate 不破坏数据
  test_partial_failure_recovery.py
```

**通过标准**：所有 fixtures 跑完后 `resume validate` 退出码 0 或仅有 warning。

---

## 九、文档迁移辅助

`resume migrate` 完成后自动生成：

```
.resume-backup-v1/MIGRATION-REPORT.md
```

内容：

```markdown
# Migration Report: 2026-07-01

## Summary
- From: v1.3.0
- To:   v2.0.0
- Duration: 8.4s
- Files migrated: 24
- Warnings: 1

## What changed

### profile/
- self-profile.md → identity.yaml + skills/data.yaml + self-profile/data.yaml
- projects/proj-001.md → projects/proj-001-xxx/data.yaml + narrative.md
- ...

## What stayed the same

- 你的所有简历 HTML 都保留在原位置可投递
- 触发词 100% 兼容（"聊聊我的经历"、"分析这个 JD" 等）
- 工作流（5 阶段闭环）不变

## What's new

- Outcomes 跟踪: outcomes.yaml 模板已就位
- MCP server: `resume serve` 启动后可在 Cursor 等使用
- Dashboard: `resume status` 现在显示投递漏斗

## Validation report

- truth_first:    ✅ passed
- evidence_chain: ⚠️ 1 warning: K8s claim in skills/data.yaml lacks project evidence
- targeted_for_jd: ✅ passed

## Rollback

任何时候: `resume migrate --revert`
```

---

下一章：[09-roadmap.md](09-roadmap.md) — 分期落地路线图
