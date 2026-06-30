# 06 · 反馈闭环（v2 的核心创新）

> v1 是开环：用户用完工具 → 投简历 → 系统不知道发生了什么。
> v2 是闭环：投递结果回流 → ROI 分析 → 反向优化下一份简历。
> **没有这一层，所有"针对性优化"都是凭感觉。**

---

## 一、闭环数据流

```
用户行为                  系统记录                  反向反馈

投递简历                  outcomes.yaml.event[]            ↓
  ↓                       ├ submitted                      ↓
HR 已读                    ├ response                       ↓
  ↓                       ├ interview_invitation           ↓
邀面                       ├ interview_round_N              ↓
  ↓                       ├ final_result                   ↓
面试                       └ offer                          ↓
  ↓                                                         ↓
反馈                       roi_analyzer.py 派生              ↓
  ↓                       ├ funnel rates                   ↓
Offer/拒                   ├ best resumes                  ↓
                          ├ weak spots                     ↓
                          └ channel effectiveness          ↓
                                                            ↓
                          下次 output / coach 的输入  ←─────┘
```

---

## 二、`outcomes.yaml` 设计

详见 [02-data-layer-spec.md §4.7](02-data-layer-spec.md)。这里强调几点设计原则：

### 2.1 Append-only event log

```yaml
events:
  - id: evt-001
    timestamp: ...
    type: submitted
    detail: {...}
  - id: evt-002
    timestamp: ...
    type: response
    detail: {...}
```

**永远只追加，不删不改**。原因：
- 求职过程有反复（拒了又邀、谈崩了又复活），删事件会丢上下文
- event log 可被 `roi_analyzer` 重放
- 是 audit trail，用户回顾"我去年面试到底卡哪了"也用得上

### 2.2 Event 类型枚举

```yaml
event_types:
  submitted:              # 投递
    required: [channel]
    optional: [method, notes, cover_letter_used]
  response:               # 收到任何回应（非沉默）
    required: [response_type]
    response_types: [hr_screen, interview_invitation, rejection, request_more_info, ghosted_after_N_days]
  interview:              # 一轮面试
    required: [round, type, result]
    types: [phone_screen, technical, behavioral, system_design, hr, final, take_home]
    optional: [interviewer_feedback, questions_struggled_with[], questions_aced[], duration_minutes]
  pause:                  # 流程暂停
    optional: [reason]
  resume_after_pause:
    optional: [reason]
  offer:
    optional: [salary_total, equity, base, signing_bonus]
  final_result:
    required: [outcome]   # offer / rejected / withdrew / ghosted
    optional: [reason, lessons_learned]
  user_note:              # 用户随时记录的备忘
    required: [content]
```

### 2.3 隐私

`outcomes.yaml` 可能含**真实的薪资信息和拒信内容**，敏感等级高于其他档案。建议：

- 在 `.gitignore` 默认排除 `outcomes.yaml`（用户可选 opt-in）
- `resume export` 时**不**包含 outcomes 数据
- `traces/` 日志中 outcomes 相关 trace 自动脱敏

---

## 三、`resume track` 入口设计

### 3.1 对话式（推荐）

```
用户: 上周投的拉勾后端简历，HR 说我 K8s 经验不够，直接拒了
agent: [意图识别: track.final_result, reason=K8s 经验不足]
       要记录到 jd-005-拉勾后端/outcomes.yaml 吗？(y/edit/n)
       - type: final_result
       - outcome: rejected
       - reason: "K8s 经验不足"
       - source: HR 反馈
用户: y
agent: ✅ 已记录。
       基于你最近的反馈，"K8s" 关键词在 3/8 次投递中被提到为短板。
       要现在制定 K8s 学习计划吗？
```

### 3.2 命令式（脚本/CI）

```bash
resume track submitted jd-005 --channel=拉勾
resume track interview jd-005 --round=1 --type=technical --result=passed \
  --feedback="Python 扎实，分布式一般" \
  --struggled-with="Raft,K8s networking"
resume track final-result jd-005 --outcome=rejected --reason="K8s 经验不足"
resume track offer jd-007 --salary-total="35k*16" --accepted=false
```

### 3.3 主动提醒

`resume status` 检测：

```
⏰ 提醒
  jd-005-拉勾后端 投递已 14 天，无任何 event。
  要标记为 ghosted 吗？(y/n/snooze)
```

---

## 四、`roi_analyzer.py`

### 4.1 输入

```
resumes/*/outcomes.yaml
```

### 4.2 输出（写到 .resume-cache/derived/）

```yaml
schema_type: roi_report
generated_at: ...
period: last_30d  # / all_time / custom

funnel:
  submitted: 8
  responded: 5
  interview_invited: 3
  interview_passed_round_1: 2
  offer_received: 1
  offer_accepted: 1

conversion:
  submit_to_response: 0.625
  response_to_invitation: 0.600
  invitation_to_offer: 0.333

best_performing:
  by_response_rate:
    - resume_id: resume-v3
      jd_id: jd-001
      template: tech-modern
      response_rate: 1.0
      sample_size: 2
  by_close_rate:
    - resume_id: resume-v1
      jd_id: jd-007
      offer_received: true
      total_days: 12

weak_spots:                # 面试反馈出现 ≥2 次的关键词
  - topic: Raft 协议
    mentioned_in_events: [evt-003, evt-007, evt-011]
    suggested_action: "resume learn raft"
    urgency: high
  - topic: K8s networking
    mentioned_in_events: [evt-003, evt-009]
    urgency: medium

channels:
  拉勾: {submitted: 3, response_rate: 0.67}
  Boss: {submitted: 3, response_rate: 0.33}
  内推: {submitted: 2, response_rate: 1.00}

template_performance:
  tech-modern:   {used: 4, response_rate: 0.75}
  tech-standard: {used: 4, response_rate: 0.50}

insights:                  # 由规则引擎生成，给 status 显示
  - "内推渠道转化最高（2/2），考虑加大投入"
  - "tech-modern 模板表现优于 tech-standard，下次默认用 modern"
  - "Raft 已被 3 次提到，最高优先级补"
```

### 4.3 规则引擎（可读性优先）

```python
# resume_alchemist/tools/roi_rules.py
def insight_rules(report: RoiReport) -> list[Insight]:
    insights = []

    # 规则 1: 渠道效率
    best_channel = max(report.channels.items(), key=lambda x: x[1].response_rate)
    if best_channel[1].submitted >= 2 and best_channel[1].response_rate > 0.6:
        insights.append(Insight(
            text=f"{best_channel[0]} 渠道转化最高，考虑加大投入",
            confidence=0.8,
        ))

    # 规则 2: 模板对比
    if len(report.template_performance) >= 2:
        sorted_t = sorted(report.template_performance.items(),
                          key=lambda x: x[1].response_rate, reverse=True)
        if sorted_t[0][1].used >= 3 and sorted_t[0][1].response_rate > sorted_t[1][1].response_rate + 0.2:
            insights.append(Insight(
                text=f"{sorted_t[0][0]} 模板优于 {sorted_t[1][0]}，建议默认用之",
            ))

    # 规则 3: 弱点优先级
    for spot in report.weak_spots:
        if spot.urgency == "high":
            insights.append(Insight(
                text=f"{spot.topic} 已被 {len(spot.mentioned_in_events)} 次提到，建议优先学",
                action=Action(skill="output", target="learning", args={"focus": spot.topic}),
            ))

    return insights
```

**规则可读、可单测、可让用户在 `templates/user/roi_rules.yaml` 自定义。**

---

## 五、Coach 怎么用这些反馈

### 5.1 在 `output --target resume` 时

```python
def build_resume(jd_id, ...):
    report = roi_analyzer.load_latest()
    coach = get_coach(state.target_role)

    suggestions = []

    # 反馈影响模板选择
    if report.template_performance:
        best_template = max(report.template_performance.items(),
                            key=lambda x: x[1].response_rate)
        suggestions.append(f"推荐用 {best_template[0]}（历史响应率 {best_template[1].response_rate:.0%}）")

    # 反馈影响内容侧重
    if report.weak_spots:
        suggestions.append("简历应避免突出 " + ", ".join(s.topic for s in report.weak_spots[:2]))

    return coach.build_with_feedback(jd_id, suggestions)
```

### 5.2 在 `output --target interview` 时

```python
def prepare_interview(jd_id):
    report = roi_analyzer.load_latest()
    coach = get_coach(state.target_role)

    # 历史被追问的弱点必须重点练
    practice_topics = [s.topic for s in report.weak_spots]

    return coach.generate_interview_guide(
        jd_id,
        priority_topics=practice_topics,
    )
```

### 5.3 在 `output --target learning` 时

```python
def make_learning_plan(skill):
    report = roi_analyzer.load_latest()

    # 把弱点排到学习计划最前
    return [
        *make_subplan(s.topic, urgency=s.urgency)
        for s in report.weak_spots
    ] + base_plan(skill)
```

---

## 六、Dashboard 体验（在 status 中）

### 6.1 漏斗可视化（终端 ASCII）

```
[投递漏斗 · 最近 30 天]

  投递   ████████████████████ 8
  回应   ████████████ 5 (62%)
  邀面   ████████ 3 (60%)
  终面   █████ 2 (67%)
  Offer  ██ 1 (50%)

  总转化率: 1/8 = 12.5%
  对照同期同行（可选数据）: 平均 8%
```

### 6.2 横向对比

```
[最近 5 份简历表现]

  resume-id        jd-id       template     模板分  响应  邀面  Offer
  ─────────────────────────────────────────────────────────────────
  resume-v3 (j01)  jd-001      tech-modern  85    ✓     ✓     pending
  resume-v1 (j02)  jd-002      tech-modern  72    ✓     ✗     —
  resume-v2 (j03)  jd-003      tech-standard 68    ✗     —     —
  resume-v1 (j07)  jd-007      tech-modern  88    ✓     ✓     ✓
  resume-v1 (j09)  jd-009      product-std  55    ✗     —     —    ← 跨界投递，表现差
```

### 6.3 周/月报

```bash
resume status --period last_7d
resume status --period 2026-06    # 某月
resume status --since-last-status  # 上次看 status 之后的变化
```

---

## 七、隐私边界

| 数据 | 是否入 git（默认） | 是否随 export 携带 | 是否进 LLM 上下文 |
|---|---|---|---|
| `profile/` | ✅ | ✅（renderer 输出） | ✅ |
| `resumes/<jd>/jd.yaml` | ✅ | — | ✅ |
| `resumes/<jd>/resume-v*.yaml` | ✅ | ✅ | ✅ |
| `resumes/<jd>/outcomes.yaml` | ❌ 默认排除 | ❌ | ⚠️ 可选 |
| `.resume-cache/traces/*.yaml` | ❌ | ❌ | ❌ |
| `.resume-cache/derived/roi-report.yaml` | ❌ | ❌ | ⚠️ 摘要可入 |

用户可在 `.resume-config.yaml` 显式 opt-in / opt-out。

---

## 八、与 Review (盲评估) 的关系

| 维度 | review (盲评) | track + roi (反馈) |
|---|---|---|
| 视角 | 内部模拟评估 | 真实外部信号 |
| 信号源 | LLM 自己 | 真实 HR / 面试官 / Offer |
| 用途 | build 前的自检 | build 后的复盘 |
| 信任度 | 中（LLM 主观） | 高（市场真实反馈） |

**两者互补**：盲评给"出门前最后一面镜子"，反馈给"上场后的体检报告"。

---

## 九、外部信号集成（可选/未来）

未来可考虑（v2.x，非必须）：

| 来源 | 集成方式 |
|---|---|
| Gmail / Outlook | 用户授权后，自动识别邀面/拒信邮件 → 提示用户 track |
| LinkedIn 通知 | API（受限）/ 浏览器扩展 |
| HR ATS 状态页 | 部分公司有公开页，可自动监测 |

**v2.0 不做这些**，保留扩展点。

---

## 十、对方法论的影响

### 10.1 三条原则的扩展

v1：真实性 / 针对性 / 证据链

v2 在反馈层新增**第 4 条隐含原则**：

> **可学习原则 (Learn-from-Reality)**：所有"针对性优化"必须有真实反馈做闭环验证，否则只是 LLM 的自我感动。

这不是替代前 3 条，而是给"针对性"一个可量化的兑现路径。

### 10.2 5 阶段闭环升级

v1 闭环：

```
深挖经历 → 分析 JD → 定制简历 → 面试准备 → 学习补充 → (回到深挖)
```

v2 闭环（加 2 个节点）：

```
深挖经历 → 分析 JD → 定制简历 → [盲评校准] → 投递 → [反馈记录] → 面试准备 → 学习补充 → (回到深挖)
                                    ↑                ↓
                                    └──── coach 调整 ─┘
```

---

下一章：[07-ux-improvements.md](07-ux-improvements.md) — 交互人性化
