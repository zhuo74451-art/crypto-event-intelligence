# Market Radar v1.9A-S1 Schema Contract — Handoff

Generated: 2026-06-04 11:17:44 UTC+8
Task: v1.9A-S1 Schema Contract 补丁
Executor: claude_code_executor
Lane: 1
Project: market_radar

## Summary

v1.9A-S1 补齐了 v1.9A 缺失的最小 Schema 单源契约。所有 16 项测试通过（10 项原有 + 4 项 Schema 新增 + 2 项子测试）。

## Files Created

| File | Description |
|---|---|
| `schemas/market_radar_v19.json` | JSON Schema contract with 12 Strict Core + 8 Flexible Payload fields |
| `results/market_radar_v19_manifest_sample.json` | Complete sample manifest with all Strict Core fields populated |
| `results/market_radar_sender_v19a_schema_test_report.md` | Schema-specific test report |
| `runs/market_radar/v19a_schema_contract_handoff_20260604_111744.md` | This handoff file |

## Files Modified

| File | Changes |
|---|---|
| `scripts/market_radar_sender.py` | Added `load_schema()`, `validate_manifest()`, `build_manifest_from_paths()`; added `warnings` + `logging` imports |
| `scripts/test_market_radar_sender_v19a.py` | Added 4 new schema tests (11-14); updated imports and docstring |
| `docs/market_radar_sender_v19a.md` | Added v1.9A-S1 Schema Contract section; updated file listing and test coverage |

## 1. Schema 如何成为 Sender 的单源契约

- **字段定义集中化**：所有字段名、类型、必填性定义在 `schemas/market_radar_v19.json` 中，sender 不硬编码任何字段列表
- **`validate_manifest()` 动态读取**：从 schema 的 `strict_core_field_names` 和 `flexible_payload_field_names` 数组读取，新增字段只需修改 schema JSON
- **`build_manifest_from_paths()` 标准化输出**：generator 使用此函数生成符合 schema 的 manifest，保证 sender/history 消费端格式一致
- **去硬编码**：sender 原有字段逻辑（如 max_send_count、blocked）已经可以由 manifest 驱动，未来逐步迁移

## 2. Strict Core 和 Flexible Payload 分别有哪些字段

### Strict Core (12 fields — 缺失 → ValueError)

| # | Field | Type | Default |
|---|---|---|---|
| 1 | `artifact_id` | string | auto-generated |
| 2 | `project_label` | string | "market_radar" |
| 3 | `created_at` | string (ISO 8601) | now() |
| 4 | `candidate_md_path` | string | — |
| 5 | `candidate_json_path` | string | — |
| 6 | `preview_report_path` | string | — |
| 7 | `parse_mode` | string | "HTML" |
| 8 | `target_type` | string | "TG群" |
| 9 | `max_send_count` | integer | 1 |
| 10 | `blocked` | boolean | false |
| 11 | `leak_count` | integer | 0 |
| 12 | `full_address_count` | integer | 0 |

### Flexible Payload (8 fields — 缺失 → Warning only)

| # | Field | Type |
|---|---|---|
| 1 | `token_name` | string\|null |
| 2 | `symbol` | string\|null |
| 3 | `wallet_short` | string\|null |
| 4 | `side` | string\|null |
| 5 | `pnl` | number\|string\|null |
| 6 | `entry_price` | number\|string\|null |
| 7 | `liquidation_distance` | number\|string\|null |
| 8 | `extra_context` | object\|null |

## 3. v1.9B 接 FakeTransport / TGTransport 时如何复用该 schema

1. **FakeTransport**：
   - 读取 manifest 的 `target_type`（设为 `"fake"`）
   - 使用 `validate_manifest()` 校验输入
   - 模拟 `send_message()` 但不调用 TG API
   - 返回 mock `message_id`

2. **TGTransport**：
   - 读取 manifest 的 `target_type`（`"TG群"` / `"TG频道"`）
   - 使用 `validate_manifest()` 校验输入
   - 读取 `max_send_count` 防重复发送
   - 读取 `parse_mode` 用于 TG API 渲染

3. **共享 Schema**：
   - 两种 Transport 都通过 `load_schema()` → `validate_manifest()` 获取字段规则
   - 不各自散落硬编码字段列表
   - 新增字段（如 `chat_id`、`token_ref`）可归类为 Flexible Payload，直接加入 schema JSON，不影响现有代码

## Test Results

```
Total: 16
Passed: 16
Failed: 0
Skipped: 0
```

## Blocker / Warning / Suggestion

- **No blockers** — all tests pass, all files created
- **Warning**: Flexible Payload warnings are emitted as `UserWarning` during `validate_manifest()`. In production, callers should use `warnings.catch_warnings()` to suppress when appropriate.
- **Suggestion**: v1.9B should add a `transport` field to the schema (Flexible Payload) to distinguish fake vs real transport modes without changing the existing schema contract.
