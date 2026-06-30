# 状态文件 Schema (State Schema)

被所有子 skill 引用。`.resume-state.json` 是各子 skill 共享上下文的**单一来源**。

---

## 文件位置

```
<user-resume-project>/.resume-state.json
```

**绝不**放到全局 `~/.claude/` 或 resume-alchemist 自己的目录——一个用户可能维护多个求职项目，每个项目独立状态。

---

## 完整 schema

```json
{
  "schema_version": "1.0",
  "skill_version": "1.0.0",

  "target_role": "后端工程师",
  "target_industry": "互联网",
  "experience_level": "3-5年",

  "project_count": 0,
  "skill_count": 0,
  "jd_count": 0,
  "resume_count": 0,

  "last_mine_at": null,
  "last_jd_at": null,
  "last_resume_at": null,
  "last_interview_at": null,
  "last_verify_at": null,

  "active_jd_id": null,
  "pending_learning": [],

  "imported_template": null,

  "initialized_at": "2026-06-13T10:00:00+08:00"
}
```

---

## 字段说明

### 元数据

| 字段 | 类型 | 写入者 | 读取者 | 说明 |
|---|---|---|---|---|
| `schema_version` | string | resume-init / resume-migrate | 所有 skill | "1.0"。schema 升级时 bump |
| `skill_version` | string | resume-init | 所有 skill | resume-alchemist 当前版本 |
| `initialized_at` | ISO 8601 | resume-init | resume-status | 首次初始化时间，永不变 |

### 目标配置

| 字段 | 类型 | 取值 | 写入者 | 读取者 |
|---|---|---|---|---|
| `target_role` | string | 用户输入 | resume-init | resume-build, resume-jd, resume-learn |
| `target_industry` | string | 用户输入 | resume-init | resume-jd, resume-learn |
| `experience_level` | enum | "应届" / "1-3年" / "3-5年" / "5年+" | resume-init | resume-build, resume-jd |

### 累计计数

| 字段 | 类型 | 写入者 | 用途 |
|---|---|---|---|
| `project_count` | int | resume-mine | 每次深挖 +1 |
| `skill_count` | int | resume-profile | 技能树更新时重算 |
| `jd_count` | int | resume-jd | 每次 JD 分析 +1 |
| `resume_count` | int | resume-build | 每次简历生成 +1 |

### 时间戳

| 字段 | 类型 | 写入者 |
|---|---|---|
| `last_mine_at` | ISO 8601 / null | resume-mine |
| `last_jd_at` | ISO 8601 / null | resume-jd |
| `last_resume_at` | ISO 8601 / null | resume-build |
| `last_interview_at` | ISO 8601 / null | resume-interview |
| `last_verify_at` | ISO 8601 / null | resume-verify |

### 会话状态

| 字段 | 类型 | 写入者 | 读取者 | 说明 |
|---|---|---|---|---|
| `active_jd_id` | string / null | resume-jd | resume-build, resume-interview | 当前活跃的 JD ID |
| `pending_learning` | array | resume-learn | resume-status, resume-learn | 待学习技能列表 |
| `imported_template` | string / null | resume-import | resume-build | 用户通过导入保留的模板路径，如 `templates/imported/my-resume.html`。null 表示未导入模板 |

---

## 读写协议

### 读（任何 skill）

```python
import json, os

def read_state():
    state_path = os.path.join(os.getcwd(), ".resume-state.json")
    if not os.path.exists(state_path):
        # 不存在 = 用户没初始化，路由到 /resume-init
        raise NeedsInitError()

    with open(state_path) as f:
        state = json.load(f)

    # 检查 schema_version 兼容
    LATEST_SCHEMA = "1.0"
    if state.get("schema_version") != LATEST_SCHEMA:
        log_warning(f"schema 版本不匹配：state={state.get('schema_version')}, 期望={LATEST_SCHEMA}")

    return state
```

### 写（任何 skill）

```python
import json, os

def write_state(state):
    state_path = os.path.join(os.getcwd(), ".resume-state.json")
    tmp_path = state_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, state_path)  # atomic rename
```

**关键纪律**：
- **原子写**：写到 .tmp → rename。避免半写损坏的 state file
- **永远 indent=2**：人类可读，便于用户手改 + git diff
- **ensure_ascii=False**：保留中文字符不转 \uXXXX
- **用 `.get(field, default)` 容错**：新版 skill 引入新字段时旧 state file 会缺该字段

---

## 字段写入责任表

**绝不允许**多个 skill 写同一字段——会导致状态语义破碎。

| 字段 | 唯一写入者 | 何时写 |
|---|---|---|
| `target_role` | resume-init | 初始化时 |
| `target_industry` | resume-init | 初始化时 |
| `experience_level` | resume-init | 初始化时 |
| `project_count` | resume-mine | 每次深挖后 |
| `skill_count` | resume-profile | 技能树更新时 |
| `jd_count` | resume-jd | 每次 JD 分析后 |
| `resume_count` | resume-build | 每次简历生成后 |
| `last_mine_at` | resume-mine | 每次深挖后 |
| `last_jd_at` | resume-jd | 每次 JD 分析后 |
| `last_resume_at` | resume-build | 每次简历生成后 |
| `last_interview_at` | resume-interview | 每次面试准备后 |
| `last_verify_at` | resume-verify | 每次代码验证后 |
| `active_jd_id` | resume-jd | 每次 JD 分析后 |
| `pending_learning` | resume-learn | 学习计划更新时 |
| `imported_template` | resume-import | 用户选择保留原始模板时 |

---

## state file 损坏处理

| 症状 | 处理 |
|---|---|
| 文件不存在 | 提示"未初始化，请跑 /resume-init"，**不**自动创建 |
| JSON 解析失败 | 提示"state file 损坏"，建议手动修复或重跑 init |
| schema_version 不识别 | 提示版本号 + 建议跑 /resume-migrate |
| `pending_learning` 含已删除的文件 | resume-status 检测时安静移除 |

---

## 与 git 的关系

`.resume-state.json` **应该**被纳入 git：
- ✅ 它是项目配置 + 累计指标的快照
- ✅ git history 提供状态演化的完整轨迹
- ✅ 多设备同步靠 git push/pull
- ❌ **不**含敏感信息（密码 / API key 应放 `.env`）

`.resume-cache/` 目录**不应该**被纳入 git：
- 含临时缓存文件
- 这些是设备本地状态，跨设备同步无意义

---

## 升级路径

未来 schema 变化时：
1. bump `schema_version`（如 "1.0" → "1.1"）
2. 写 `migrations/<old>-to-<new>.md`
3. 改 `migrations/registry.md`
4. **绝不**让 skill 静默兼容旧版 schema
