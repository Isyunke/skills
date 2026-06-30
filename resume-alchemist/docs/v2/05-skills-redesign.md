# 05 · Skill 包重构（13 → 7）

> v1 的 13 个 sub-skill 有大量职责重叠（mine/import/verify 都是"录入"；build/optimize/localize 都是"产出"）。
> v2 用**动词模型**重新组织：3 个动词 + 4 个引擎，共 7 个 skill。
> 每个 skill 通过"模式参数"或"阶段子命令"覆盖原来的多个细分场景。

---

## 一、合并对照表

| v2 Skill | 类型 | 合并自 v1 | 主要变化 |
|---|---|---|---|
| `intake` | 动词·录入 | mine + import + verify | 三种 mode（dialog/file/code）合一 |
| `match` | 动词·匹配 | jd | 输出从 markdown 升级为 jd.yaml + match-report.yaml |
| `output` | 动词·产出 | build + optimize + interview + learn + export + localize | 用 `--target` 子命令选输出物 |
| `profile` | 引擎·档案 | profile | 加 show-me 模式 |
| `review` | 引擎·盲评 | blind | 升级为通用隔离评估，能评 resume / interview / jd 三种 |
| `status` | 引擎·看板 | status | 升级为真·dashboard（接 outcomes） |
| `coach` | 引擎·教练 | （新） | 角色化人格注入 |
| `track` | 动词·反馈（隐式） | （新） | 投递结果记录 |

注：`track` 在概念上独立，但实现上是 `feedback-loop` 引擎的入口，没单列为引擎。

**总计：7 个一等 skill** + 1 个 `coach` 引擎横向注入。

---

## 二、`intake`（动词·录入）

### 替代

- `resume-mine`（对话深挖）
- `resume-import`（文件导入）
- `resume-verify`（代码溯源）

### 三个 mode

```yaml
skill_id: intake
modes:
  dialog:        # 对话深挖（原 mine）
    inputs: [project_topic?]
    method: STAR 引导
  file:          # 文件导入（原 import）
    inputs: [resume_file_path]
    method: parser.py 解析 + 用户确认
  code:          # 代码溯源（原 verify）
    inputs: [project_path]
    method: 代码扫描 + 知识验证提问
```

### 触发词

```yaml
intent_triggers:
  zh:
    - 聊聊我的经历       → mode=dialog
    - 深挖一下           → mode=dialog
    - 导入简历           → mode=file
    - 我有简历           → mode=file
    - 解析我的简历       → mode=file
    - 这是我的项目代码    → mode=code
    - 验证项目           → mode=code
  en:
    - deep dive          → mode=dialog
    - import resume      → mode=file
    - verify my project  → mode=code
```

### 共同输出

无论哪个 mode，最终都落到同一个 schema：

```
profile/projects/<id>/data.yaml
```

`mode=dialog` 走 STAR；`mode=file` 走 parser + 用户 confirm；`mode=code` 走代码溯源 + 知识验证。**这才是真正的"录入"。**

### 关键改进

| v1 | v2 |
|---|---|
| 三个 skill 各自维护一套 schema 写入逻辑 | 都调用 `tools.intake.commit(draft)` |
| import 和 verify 不共享"验证状态" | 统一到 `data.yaml.verified_by` 字段 |
| 用户记不住该用哪个 | agent 根据用户提供的输入自动判断 mode |

### Auto-detect mode

```python
def detect_intake_mode(user_input: str, attached_files: list[Path]) -> str:
    if attached_files and is_resume_file(attached_files[0]):
        return "file"
    if attached_files and is_code_dir(attached_files[0]):
        return "code"
    if "代码" in user_input or "code" in user_input.lower():
        return "code"
    if "简历" in user_input and ("导入" in user_input or "import" in user_input):
        return "file"
    return "dialog"
```

---

## 三、`match`（动词·匹配）

### 替代

- `resume-jd`

### 输入

```yaml
inputs:
  - jd_text: 直接粘贴的 JD 文本
  - jd_url:  招聘网站链接（自动抓取，注意合规）
  - jd_file: 本地 JD 文件
```

### 输出

```
resumes/jd-<NNN>-<short>/
  jd.yaml            ← 结构化 JD（由 keyword_extractor 产）
  jd-analysis.md     ← narrative 渲染
  match-report.yaml  ← 匹配度报告（由 match_scorer 产）
  match-report.md
```

### 关键改进

| v1 | v2 |
|---|---|
| JD 分析全靠 LLM 自由文本 | LLM 只负责"理解 JD 语义" + 把结果塞进结构化 yaml |
| 匹配度由 LLM 估算 | 由 match_scorer.py 5 个维度加权打分 |
| 不区分 must_have / nice_to_have | 强制分级，影响后续 build 时取舍 |
| 不出"gap → recommendation" | match-report 自带 `recommendations.for_resume / for_interview / for_learning` |

### 升级：JD URL 抓取

```bash
resume match --url https://www.lagou.com/jobs/xxx.html
```

注意事项：
- 仅抓取公开页面
- 加 User-Agent 标识自己是工具
- 失败时降级提示"请直接粘贴 JD 文本"

---

## 四、`output`（动词·产出）

### 替代

- `resume-build`（生成简历）
- `resume-optimize`（优化简历）
- `resume-interview`（面试指南）
- `resume-learn`（学习计划）
- `resume-localize`（本地化）
- `resume-export`（导出 PDF）

### 用 `--target` 选输出物

```bash
resume output --target resume       # 生成/重生成简历
resume output --target interview    # 面试指南
resume output --target learning     # 学习计划
resume output --target localized --locale en-US
resume output --target export --format pdf
resume output --target optimize --focus star,quantification
```

### 触发词

```yaml
intent_triggers:
  zh:
    - 生成简历 / 针对这个 JD 优化简历  → target=resume
    - 优化简历 / 改改简历              → target=optimize
    - 准备面试 / 模拟面试              → target=interview
    - 学什么 / 学习计划                → target=learning
    - 转英文简历 / 中英文转换           → target=localized
    - 导出 PDF / 生成 PDF              → target=export
```

### 关键改进

| 子命令 | 改进 |
|---|---|
| `resume`     | LLM 不再直接拼 HTML；通过 renderer.py 走 Jinja2 |
| `optimize`   | 输出 diff（before/after + 解释），不再静默改 |
| `interview`  | 升级为**交互式模拟面试**（详见下节 §四.4） |
| `learning`   | 引用 outcomes.yaml 的弱点信号，优先推弱点相关技能 |
| `localized`  | 走 i18n.py 文化适配规则，不是逐句翻译 |
| `export`     | 调 exporter.py，pre-flight 校验环境 |

### 4.1 `output --target resume`

```
[读取 jd.yaml + match-report.yaml + profile/]
  ↓
[选模板（默认按 target_role；用户可覆盖）]
  ↓
[组装 resume-v<N>.yaml]
  ↓
[validator 强制校验（不通过则阻断）]
  ↓
[review.blind 盲评估（可选；默认开）]
  ↓
[renderer 产出 HTML]
  ↓
[提示用户下一步：optimize / export / interview]
```

### 4.2 `output --target optimize`

新增**diff 视图**：

```
📊 优化提案 (resume-v1 → resume-v2)

[Section: summary]
  - 4 年互联网后端经验...
  + 4 年互联网后端经验，专注高并发性能优化（P99 降低 81%）...
  原因：JD 强调"性能优化"，量化数据前置抓眼球

[Section: skills.programming]
  ~ 调整顺序：Python, Java, Go → Python, Go, Java
  原因：JD 频繁出现 Go，但你 Java 证据更强；折中：把 Go 前置但不夸大

[Section: projects.proj-001]
  + 增加一句："采用 Raft 协议实现分布式一致性"
  原因：JD 关键词覆盖 "Raft"

匹配度：72 → 81 (+9)
确认应用？ y/n/edit
```

`edit` 模式让用户逐条接受/拒绝。

### 4.3 `output --target interview`

升级为**两段式**：

```yaml
mode_a: prep    # 生成面试指南（v1 行为）
mode_b: live    # 实时模拟面试（新增）
```

`mode_b` 是 v2 的杀手锏：

```
agent: 准备好了我们开始。我会模拟一轮技术面，60 分钟。
        我先问第一题。

agent: 介绍一下你最有挑战的项目。

用户:  我做了 XX 系统的性能优化...

agent: [STAR 完整度评估]
        S/T/A/R 都有，但 Action 太笼统。请具体说一下：
        你说"优化了 SQL"——是怎么定位到 SQL 是瓶颈的？

用户:  用 Py-Spy 看的火焰图...

agent: [追问深度评估]
        ✓ 好。继续。如果当时 Py-Spy 不能用，你会怎么 profile？

...

[面试结束]

📊 面试评分（jd-001 mock interview #1）

  整体: 7.5/10

  按问题:
  Q1 项目深挖:        8/10 — STAR 完整，追问到位
  Q2 Raft 协议:       4/10 — 卡在 leader election 细节
  Q3 K8s networking:  3/10 — 概念混淆 service vs ingress
  Q4 行为题:          8/10 — 例子真实有数据

  弱点（已记录到 jd-001/outcomes.yaml）:
    - Raft leader election
    - K8s service vs ingress

  推荐学习:
    1. Raft 论文 4.2 节（30 min）
    2. K8s 网络模型（2h）
```

弱点会**自动回流到 outcomes.yaml**，下次 `coach` 准备时会考虑。

### 4.4 `output --target export`

```bash
resume export --format pdf       # 默认
resume export --format docx
resume export --format jsonresume
resume export --format markdown   # GitHub 主页
resume export --format plaintext  # ATS 友好
resume export --format all        # 一次导出所有
```

预检：

```bash
resume export --check
# → playwright: ✅ (chromium installed)
#   weasyprint: ⚠️ (GTK 未安装，Windows 推荐用 playwright)
#   docx: ✅ (python-docx)
```

---

## 五、`profile`（引擎·档案）

### 替代

- `resume-profile`

### 改进

新增**模式参数**：

```bash
resume profile show              # 总览（renderer 渲染）
resume profile show skills       # 只看技能树
resume profile show projects     # 只看项目列表
resume profile show timeline     # 时间线视图
resume profile edit identity     # 修改基本信息（打开 yaml）
resume profile gaps              # 列出"声明了但无证据"的技能
```

### Show-me 模式

任意时候用户说 `show me X` 或 `看看我的 X`，全局触发：

```yaml
global_intent: show_me
pattern: (?:show me|show|看看)\s+(profile|skills|projects|jds|resumes|outcomes)
action: profile.show {section}
```

输出**渲染后的 markdown**（不是裸 yaml），美观即时。

---

## 六、`review`（引擎·盲评）

### 替代

- `resume-blind`

### 升级：从"盲评简历"到"通用隔离评估"

v1 的 `resume-blind` 只能评简历。v2 升级为：

```bash
resume review resume RESUME_ID JD_ID    # 盲评简历（原 blind）
resume review interview JD_ID            # 评估面试表现（输入 outcomes events）
resume review jd JD_ID                   # 评估 JD 本身（是否符合用户目标）
```

每种评估都用**隔离 sub-agent**（context isolation），保留 v1 的核心思想：

```python
def review_resume(resume_path, jd_path):
    # spawn 隔离 sub-agent
    spawn_subagent(
        prompt=BLIND_REVIEW_PROMPT,
        allowed_reads=[resume_path, jd_path],
        denied_reads=ALL_OTHER_PATHS,
    )
```

### 输出

严格 JSON（与 v1 兼容）：

```yaml
schema_type: review_report
target: resume  # / interview / jd
dimensions:
  keyword_match:   {score, weight, reason}
  quantification:  {...}
  star_completeness: {...}
  relevance:       {...}
  presentation:    {...}
overall_score: 7.4
suggestions: [...]
self_check:
  any_contamination_signal: false
```

---

## 七、`status`（引擎·看板，升级为真·dashboard）

### 替代

- `resume-status` + 新接入反馈数据

### 输出（升级版）

```
📊 简历炼金术士 · 状态看板

[目标]
  后端工程师 · 互联网 · 3-5y

[档案]
  项目数:  5（其中 2 个代码验证、1 个文件导入、2 个对话深挖）
  技能数:  18（强证据 12 / 弱证据 5 / 无证据 1）⚠️
  JD 数:   3
  简历:    5 份（jd-001:2版, jd-002:1版, jd-003:2版）

[最近 30 天投递漏斗]
  投递 → 回应 → 邀面 → 终面 → Offer
   8  →  5  →  3  →  2  →  1
  转化率:  62% / 60% / 67% / 50%

[最高 ROI 简历]
  resume-v3 (jd-001, 用 tech-modern 模板): 邀面率 67%

[弱点分布（基于面试反馈）]
  Raft / 分布式一致性:  被追问 3 次
  K8s 网络:             被追问 2 次
  系统设计大题:          被追问 2 次

[建议]
  → 优先补 Raft 知识（30min 论文 4.2 节）
  → 把 K8s 经验明确写"了解"避免被深挖
  → 调整下次 build 时跳过 jd-002（与目标偏离大）

[Tip]
  最近一份简历距今 7 天，建议针对新 JD 重新校准。
```

### 不再依赖 `.resume-state.json`

`status` 调 `tools.state_builder.build_state()` 实时从 KB + outcomes 派生。

---

## 八、`coach`（引擎·角色化教练，**v2 新增**）

### 为什么需要

v1 的所有 skill 都用同一套话术。但**技术岗深挖** ≠ **PM 岗深挖** ≠ **设计岗深挖**：

| 维度 | 技术教练 | PM 教练 | 设计教练 |
|---|---|---|---|
| STAR 重点 | Action 的技术细节 | Action 的决策过程 | Action 的设计思考 |
| 量化方式 | 性能/规模/吞吐 | 增长/留存/转化 | 用户满意度/可用性测试 |
| 追问方向 | "为什么用 X 不用 Y" | "你怎么说服 stakeholder" | "你做了几轮 user testing" |
| 简历模板 | tech-modern/standard | product-standard | design-creative |
| 行业词包 | tech.yaml | product.yaml | design.yaml |
| 面试题库 | 数据结构/算法/系统设计 | 产品 case / 估算 / 增长 | 作品集 walkthrough / 设计批判 |

### 实现

`coach` 不是用户直接调用的 skill，而是**横向注入**：

```python
# 任何 skill 启动时
class SkillContext:
    coach: CoachPersona = inject_coach(state.target_role)

    def intake_question(self):
        return self.coach.frame_question("intake")

    def review_resume(self):
        return self.coach.score_resume(weights=self.coach.review_weights)
```

### Persona 定义

```yaml
# resume_alchemist/data/personas/tech.yaml
persona_id: tech
applicable_roles: [backend, frontend, fullstack, algo, sre, data, ai_ml, robotics]

voice:
  tone: 直接、技术导向、爱挖细节
  example_phrases:
    - "为什么选这个方案而不是 X？"
    - "瓶颈是 CPU 还是 IO？"
    - "压测数据呢？"

intake_focus:
  star_emphasis:
    action: 0.5      # 技术教练重点关注 Action
    result: 0.3
    situation: 0.1
    task: 0.1
  follow_up_questions:
    - "用了什么技术栈？为什么这个组合？"
    - "性能/规模/吞吐量数据？"
    - "踩过什么坑？怎么解决？"

match_weights:
  keyword_coverage: 0.30
  evidence_chain: 0.30
  quantification: 0.20
  star_completeness: 0.10
  experience_level: 0.10

review_weights: {...}

learning_resources_bias:
  prefer: [paper, source_code, hands_on]
  avoid: [marketing_articles]
```

类似的有 `product.yaml`, `design.yaml`, `sales.yaml`, `data.yaml`, `default.yaml`。

### 切换

```bash
resume coach show              # 当前 persona
resume coach use product       # 临时切换 persona（不改 target_role）
resume coach customize         # 用户定制自己的 persona
```

用户可以**继承官方 persona 然后改几个字段**：

```yaml
# templates/user/personas/my-tech.yaml
extends: tech
voice:
  tone: 直接、技术导向、爱挖细节，但温和一点  # 个人偏好
match_weights:
  quantification: 0.30   # 我特别看重量化
```

---

## 九、`track`（反馈记录入口）

### 触发词

```yaml
intent_triggers:
  zh:
    - 我投了 / 投了简历
    - 收到面试邀请
    - 面试结束 / 面完了
    - 收到拒信
    - 拿到 offer
    - 谈薪
  en:
    - submitted my resume
    - got an interview
    - interview done
    - rejected
    - got offer
```

### 流程

```
用户: 我投了拉勾那个简历
agent: [识别意图: track.submitted]
       记录到 jd-001-xx公司后端/outcomes.yaml？(y/n)
用户: y
agent: 渠道是? (拉勾/Boss/内推/官网/...)
用户: 拉勾
agent: ✅ 已记录。下次 status 会包含此次投递。
       建议在收到回应后再来 track 一次。
```

### 命令式

```bash
resume track jd-001 submitted --channel=拉勾
resume track jd-001 interview --round=1 --result=passed --feedback="..."
resume track jd-001 offer --accepted=false --reason="..."
```

---

## 十、跨 Skill 的共同 contracts

### 10.1 输入契约

每个 skill 启动时必须 check：

```python
def precondition_check(state, skill_id):
    rules = ORCHESTRATOR.preconditions[skill_id]
    for rule in rules:
        if not eval(rule, state):
            raise PreconditionFailed(rule, suggested_skill=...)
```

例如 `output --target resume` 的 preconditions：

```yaml
preconditions:
  - state.initialized
  - state.active_jd_id != null
  - len(state.projects) >= 1
on_failure:
  initialized: route_to.init
  active_jd_id: route_to.match
  projects: route_to.intake.dialog
```

### 10.2 输出契约

每个 skill 完成时必须：

1. 调 `tools.evidence_validator` 校验自己写入的 yaml
2. 调 `tools.renderer` 重新渲染受影响的 narrative.md
3. 调 `tools.state_builder.refresh()` 更新派生 state
4. 返回 `next_suggestions: [...]` 给用户

```python
class SkillResult(BaseModel):
    success: bool
    written_files: list[Path]
    next_suggestions: list[Suggestion]
    metrics: dict       # 用于 status dashboard
```

---

## 十一、对照表：v1 触发词 → v2 skill

完整保留 v1 的所有触发词（兼容性要求），路由到新 skill：

| v1 触发词 | v1 skill | v2 skill |
|---|---|---|
| 初始化 / init | resume-init | init |
| 聊聊我的经历 / 深挖一下 | resume-mine | intake (mode=dialog) |
| 导入简历 / 我有简历 | resume-import | intake (mode=file) |
| 验证项目 / 代码溯源 | resume-verify | intake (mode=code) |
| 看看我的技能树 | resume-profile | profile show skills |
| 分析这个 JD | resume-jd | match |
| 针对这个 JD 优化简历 | resume-build | output --target resume |
| 优化一下简历 | resume-optimize | output --target optimize |
| 转换英文简历 | resume-localize | output --target localized |
| 准备面试 / 模拟面试 | resume-interview | output --target interview |
| 这个技能我不会 / 学什么 | resume-learn | output --target learning |
| 导出 PDF | resume-export | output --target export |
| 状态 / 进度 | resume-status | status |
| （盲评内部） | resume-blind | review |
| 我投了简历 / 收到面试（新） | — | track |

---

## 十二、不再保留的 v1 行为

### `truth-verification.sh` / `evidence-chain.sh`

废弃，由 `tools.evidence_validator` 取代。Hook 机制是 Claude Code 私有的，跨 agent 不通用。

### `imported_template` 字段

由 `resume-v<N>.yaml.template` 字段统一管理，不再有"导入模板"这个特殊概念。

### `project-tmd.md`

代码溯源验证过程中的临时 markdown 文件，v2 统一在 `data.yaml.verified_by + verification_score` 字段表达，不再有临时 md。

---

下一章：[06-feedback-loop.md](06-feedback-loop.md) — 反馈闭环
