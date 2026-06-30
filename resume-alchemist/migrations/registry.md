# Migration Registry

This file tracks all schema versions and migrations for resume-alchemist.

---

## Current Version

```
LATEST_SCHEMA = "1.0"
```

## Version History

| Version | Date | Type | Description |
|---|---|---|---|
| 1.0 | 2026-06-13 | MAJOR | 初始版本 |

---

## Migration Files

### 1.0 (Initial)

- **Type**: MAJOR
- **Date**: 2026-06-13
- **Description**: 初始版本
- **Breaking Changes**: 无（初始版本）

---

## Schema Evolution Rules

### MINOR (不破坏兼容)

- 新增字段：用 `state.get(field, default)` 读
- 老 state file 自动获得 default
- **仍需 bump schema_version + 写 migrations 文件**

### MAJOR (破坏兼容)

- 删除 / 重命名 / 改语义字段
- 必须 bump schema_version + 写迁移文件
- CHANGELOG 标 `BREAKING`

---

## Migration Checklist

当需要迁移时：

1. **bump schema_version**（如 "1.0" → "1.1"）
2. **写 migrations/<old>-to-<new>.md**
   - WHAT: 改了什么
   - WHY: 为什么改
   - HOW: 怎么迁移
   - Manual fallback: 手动迁移方法
3. **改本文件的 LATEST_SCHEMA**
4. **改 CHANGELOG.md**
5. **SessionStart hook 检测到不一致时自动提示用户跑 /resume-migrate**

---

## Manual Fallback

如果自动迁移失败：

1. 备份 `.resume-state.json`
2. 手动编辑 JSON，添加缺失字段
3. 更新 `schema_version` 到最新版本
4. 重新运行 `/resume-init`（如需要）

---

## Notes

- 绝不让 skill 静默兼容旧版 schema
- 新增字段用 `.get(field, default)` 容错
- 删除字段必须走 MAJOR 流程
