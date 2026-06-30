# 07 · 交互人性化

> 工具再强，用户不愿意用、记不住怎么用，也是零。
> v2 在交互层做 6 件事：冷启动短、触发词少、即时可见、改动透明、模拟真实、错误友好。

---

## 一、冷启动从"4 问"改为"3 选 1 + 自动推导"

### v1 现状

[resume-init Phase 2](../../skills/resume-init/SKILL.md) 问 4 个问题：职位、行业、经验、现有材料。

问题：
- 用户耐心阈值 30 秒，4 问已经接近极限
- 问题间相关性高（"已经有简历"→ 其他问题可从简历推导）

### v2 设计

**第一屏只问 1 个问题**：

```
🧪 简历炼金术士 v2

我帮你把求职过程从"凭感觉"变成"工程化"——3 条不可妥协原则：
真实性 / 针对性 / 证据链。

你现在是？

  a) 已经有简历，想优化
  b) 完全从零开始
  c) 看到一个 JD 想看自己合不合适
  d) 我以前用过 v1，要迁移
```

**每条路径不同**：

#### a) 已经有简历
```
agent: 把简历文件拖给我（PDF/DOCX/MD/HTML）。
用户: [拖入 file]
agent: ✅ 已解析。识别出：
       - 姓名：张三
       - 目标：后端工程师
       - 经验：4 年
       - 行业：互联网（推断）
       这些对吗？(y/edit)
```

→ 剩下的字段自动从简历推导，**用户 0 问也能起步**。

#### b) 从零开始
```
agent: 那我先问 2 个问题就够了：
       1) 目标职位？（直接说，不用选项）
       2) 工作经验大概几年？
```

**改成开放式输入 + LLM 归一化**，比"选 abcd"自然。

#### c) 看 JD
```
agent: 把 JD 贴给我（或链接）。
用户: [贴 JD]
agent: ✅ 已分析。这是后端岗，需要 Python+K8s+分布式。
       接下来你需要：a) 录入你的经历看匹配度  b) 直接看 JD 详情
```

#### d) v1 迁移
```
agent: 检测到 v1 数据（schema 1.0），正在迁移...
       [跑 resume migrate]
       ✅ 完成。你的 3 个项目、2 份简历都保留了。
       新功能：try `show me my outcomes`
```

### 设计原则

- **最小问题数**：能推就不问
- **开放式输入优先**：选项是 fallback
- **进度透明**：每步都告诉用户"接下来会发生什么"

---

## 二、Show-me 模式（即时可见）

### 触发词

```
show me my profile
show me my skills
show me my projects
show me jd-001
show me my latest resume
show me outcomes / dashboard

看看我的档案
看看我的技能
看看简历
```

### 行为

立即调 `tools/renderer.py` 渲染对应实体的 narrative，**输出到对话**（不写文件）。

例如 `show me my skills`：

```
📊 你的技能树（实时渲染自 profile/skills/data.yaml）

🟢 强证据
  - Python (expert)        proj-001, proj-003 · 5 年
  - PostgreSQL (proficient) proj-001          · 4 年
  - FastAPI (proficient)    proj-001          · 2 年
  - Redis (proficient)      proj-001          · 3 年

🟡 弱证据
  - Java (proficient)       proj-002          · 2 年
  - Docker (known)          proj-001 (mention) · 1 年

🔴 无证据 (建议移除或补充项目)
  - K8s (proficient)        — 无项目支撑

💡 建议
  - 用 intake mode=code 验证你的 K8s 经验，或降级为"了解"
```

### 关键

- **即时**：不写文件、不调 LLM 重新生成、就是渲染 yaml
- **可信**：底下角注 "实时渲染自 X.yaml"，用户知道源头
- **可下钻**：`show me proj-001` 进项目详情

---

## 三、Diff 视图（改动透明）

### 何时触发

- `output --target optimize` 默认显示 diff
- `intake mode=file` 用户 confirm 前显示"我从简历提取了什么"的 diff
- `migrate` 显示 v1 → v2 的字段映射 diff

### 格式

```
📊 Optimize Proposal · resume-v1 → resume-v2

[Section: summary]
  - 4 年互联网后端经验...
  + 4 年互联网后端经验，专注高并发性能优化（P99 ↓81%）...
  reason: JD 强调"性能优化"，量化数据前置抓眼球

[Section: skills.frameworks]
  ~ reorder: [Django, FastAPI, Spring] → [FastAPI, Django, Spring]
  reason: JD 关键词 "FastAPI" 出现 3 次

[Section: projects.proj-001.achievements[0]]
  ~ before: "P99 降低 81%"
  ~ after:  "P99 latency reduced from 800ms → 150ms (-81%)"
  reason: 英文 ATS 友好；保留量化

[Section: projects]
  - removed: proj-002 (低关联，节省一页)
  reason: 与本 JD 关键词重合度 < 20%

匹配度: 72 → 81 (+9)
✅ 校验：通过

如何继续？
  [a] 全部应用    [s] 跳过    [e] 逐条选择    [v] 详情查看
```

### 逐条选择模式

```
> e

[1/5] summary 改动 (y/n/edit)? y
[2/5] skills 顺序调整 (y/n/edit)? y
[3/5] proj-001 量化数据英化 (y/n/edit)? edit
      [打开编辑器允许你手改这一句]
[4/5] 删除 proj-002 (y/n/edit)? n      ← 用户决定保留
[5/5] ...

✅ 已应用 3/5 条改动，1 条手改，1 条跳过。
```

---

## 四、错误信息友好化

### v1 现状

部分错误信息是裸 traceback 或简短英文。

### v2 模板

每个错误都要回答 3 个问题：

```
❌ 发生了什么？
   evidence_validator 拒绝：proj-002 声明了 "expert Python" 但没有量化成果。

🤔 为什么这是个问题？
   违反"证据链原则"：expert 级别需要 ≥2 项目 + ≥1 量化成果。
   这是为了避免在面试中被追问"具体多 expert"时无话可说。

🛠 怎么修？
   你有 3 个选项：
   a) 把 proj-002 的成果量化（resume intake dialog --project proj-002）
   b) 把 Python 在 proj-002 中的熟练度降为 proficient
   c) 用 intake mode=code 加一个有量化数据的 Python 项目

   要现在选一个？ a/b/c
```

### 实现

```python
class ResumeError(Exception):
    def __init__(self, what: str, why: str, how: list[FixOption]):
        self.what = what
        self.why = why
        self.how = how

    def __str__(self):
        return TEMPLATE.format(what=self.what, why=self.why, how=self.how)
```

所有 raise 都用这个模板，**统一体验**。

---

## 五、`output --target interview --mode=live` 交互式模拟

详见 [05-skills-redesign.md §4.3](05-skills-redesign.md)。重点是：

- **真实节奏**：一题一题问，不批量
- **跟进追问**：用户回答完，agent 评估深度，决定追问还是放过
- **实时评分**：每题打分，结束给总体报告
- **弱点回流**：差的回答自动进 `outcomes.yaml.weak_spots`

```
agent: 接下来 30 分钟我模拟一轮技术面。我会逐题问你，并根据回答追问。

       开始？ (y/n/暂停)
用户:  y

agent: Q1（项目深挖）：介绍一下你最有挑战的项目。

用户:  我做了 XX 系统性能优化...
       [完整 STAR 回答]

agent: 你说"用 Py-Spy 定位"——如果当时 Py-Spy 不能用，你会怎么 profile？
       （我在追问，因为想看你对工具的依赖度）

用户:  我会用 cProfile + snakeviz，或者 perf...

agent: ✓ 不错。Q2: 解释一下 Raft 协议的 leader election...

[用户答不上]

用户:  不太清楚...

agent: 没关系。Q2 跳过，记录到弱点。继续 Q3...

[60 分钟后]

agent: 时间到。报告来了：

📊 模拟面试 #1 报告 (jd-001-xx公司后端)

总分: 7.2/10  (上次 #0 是 6.5)

强项:
  ✓ 项目深挖完整度（STAR 都到位）
  ✓ 量化数据充分（每个项目都有数字）

弱点（已记录）:
  ✗ Raft leader election     ← 上次也是这个，建议立刻补
  ✗ K8s service vs ingress

建议:
  → resume learn raft       （30min 论文 4.2）
  → resume learn k8s-networking （2h 实操）

下次再来 mock?  默认 3 天后提醒你。
```

---

## 六、对话节奏的具体规则

### 6.1 单次回复不超过 3 句话（除了报告类输出）

v1 倾向输出长文本。v2 强制：

```
❌ 不好：
   我注意到你的简历有几个问题：
   1. 缺少量化数据
   2. STAR 不完整
   3. 关键词覆盖不足
   建议你...（继续 10 行）

✅ 好：
   你的简历主要问题是"量化不足"——8 项成果只有 2 项有数据。
   要从哪个项目开始补？(proj-001 / proj-002 / 全部)
```

### 6.2 一次问一个问题

延续 v1 已有的好习惯（resume-init 单问），但在所有 skill 中**严格执行**。

### 6.3 不写"很高兴帮你"这种空话

参考 v1 的 [tone 规范](../../SKILL.md#tone--voice)：直接、专业、不谄媚。

### 6.4 主动提醒，但不打扰

```
agent: ✅ 简历已生成。
       💡 提醒：jd-005 投递已 14 天无回应。要标 ghosted 吗？

       （不想被提醒可以 resume config --no-reminders）
```

---

## 七、URL / 文件输入的标准化

### v1 现状

JD 只能粘贴文本；简历只能本地路径。

### v2 改进

```bash
resume intake file ./my-cv.pdf
resume intake file https://example.com/my-cv.pdf
resume intake file gdrive://...                # 未来扩展

resume match --jd-text "..."
resume match --jd-url https://www.lagou.com/jobs/123.html
resume match --jd-file ./jd.txt
```

输入处理 pipeline：

```python
def normalize_input(spec: str) -> bytes:
    if spec.startswith("http"):
        return fetch_url(spec)
    if Path(spec).exists():
        return Path(spec).read_bytes()
    return spec.encode()   # 当作直接文本
```

---

## 八、回滚 / Undo

### v1 现状

只能靠 git，技术门槛高。

### v2 内置 snapshot

```bash
resume snapshot               # 手动打 tag
resume snapshot --auto on     # 自动在每次 build 前打 tag
resume undo                   # 回滚上一次写入
resume snapshots list
resume snapshots restore <id>
```

底层用 git，但 UX 包装成"普通人能懂"。

---

## 九、多 agent 一致性

不论用户在 Claude Code / Cursor / ChatGPT / CLI，**核心交互模板必须一致**：

- 触发词集 100% 相同（包括中英双语）
- 输出格式（diff、报告、错误信息）100% 相同
- 报错时给出的"3 个选项"等 fallback 流程相同

实现：

- 所有"用户看到的文案"集中在 `resume_alchemist/data/messages/{zh,en}.yaml`
- Skill 只 `import message("error.evidence_chain_violated")`，不内嵌文案
- agent 适配层不修改这些文案

---

## 十、可访问性（accessibility）

| 维度 | 措施 |
|---|---|
| 视觉障碍 | 所有 ASCII 图都有等价文本描述（`status --plain`） |
| 色觉异常 | 不用红绿对比传达关键信息；emoji + 文字双标 |
| 屏幕阅读器 | CLI 输出避免装饰性字符（可 `--no-decoration`） |
| 输入受限 | 所有交互都支持键盘 / 单字符快捷选项 |

---

## 十一、国际化（i18n）

### 文案

```
resume_alchemist/data/messages/
  zh-CN.yaml
  en-US.yaml
  ja-JP.yaml  (未来)
```

### 配置

```yaml
# .resume-config.yaml
locale: zh-CN
fallback_locale: en-US
```

### 内容
- 用户档案数据：字段级双语（`name_zh / name_en`，详见 [02 数据层](02-data-layer-spec.md)）
- 工具输出：locale 切换
- 简历模板：每个模板提供 zh/en 两份

---

## 十二、用户配置文件

新增 `.resume-config.yaml`（可选）：

```yaml
schema_version: "2.0"

locale: zh-CN

ui:
  reminders: true
  diff_default_mode: interactive   # all / interactive / off
  show_principle_explanations: true

privacy:
  outcomes_in_git: false           # 默认不入 git
  traces_retention_days: 30

defaults:
  template: tech-modern
  pdf_engine: auto                 # / weasyprint / playwright
  match_threshold_for_build: 60

semantic_match: off                # 是否启用 sentence-transformers

mcp_server:
  default_transport: stdio
  http_port: 7777
  http_auth_required: true
```

用户改这一个文件，所有 skill 行为对齐。

---

下一章：[08-migration-v1-to-v2.md](08-migration-v1-to-v2.md) — 兼容性与迁移
