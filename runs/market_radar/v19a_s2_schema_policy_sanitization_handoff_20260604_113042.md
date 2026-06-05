# Market Radar v1.9A-S2 Schema / Policy / Sanitization Handoff

Generated: 2026-06-04 11:30:42 UTC+8
Component version: v1.9A-S2
Project: market_radar

## 1. schema_version 是否进入 Strict Core

**是的。** `schema_version` 已加入 `strict_core_field_names`（从 12 字段扩展到 13 字段）。

- `schemas/market_radar_v19.json`: `strict_core.fields.schema_version` 已定义，`strict_core_field_names` 包含 `schema_version`
- `validate_manifest()`: schema_version 缺失时抛出 ValueError
- `validate_and_apply_policy()`: 额外做版本匹配检查，不匹配时 errors 阻断
- 当前要求值: `"1.9A-S2"`

## 2. Runtime Source 是否已改为相对路径约束

**是的。** 三个 Runtime Source 字段已实现完整约束：

| 规则 | 实现 | 测试 |
|---|---|---|
| 必须是相对路径 | `os.path.isabs()` 检查 | Test 17 |
| 不允许 `../` 路径逃逸 | `Path.parts` 检查 `..` | Test 18 |
| 允许目录前缀: `results/`, `runs/`, `schemas/` | 前缀白名单检查 | Test 25 |
| 违反时 errors 阻断 | 错误加入 `PolicyReceipt.errors` | — |

`build_manifest_from_paths()` 现已存储相对路径（而非绝对路径），`_make_relative_path()` 做 `resolve() → relative_to(ROOT)` 转换。

## 3. PolicyReceipt 如何消费

`PolicyReceipt` 消费规则：

```python
receipt = validate_and_apply_policy(manifest, schema)

if receipt.is_blocked:       # errors 非空 → 阻断，不做下游处理
    raise BlockedError(receipt)

data = receipt.effective_data if receipt.was_adjusted else manifest
# adjusted_fields 非空 → 必须使用 effective_data

for w in receipt.warnings:   # 只记录，不阻断
    logger.warning(w)
```

关键保证：**`raw_manifest` 不被原地修改**。所有调整在 `effective_data`（deep copy）上进行。

Lane 1 策略：`max_send_count > 1` → effective_data 中修剪为 1，记录 `adjusted_fields = ["max_send_count"]`。

## 4. raw_manifest 是否保持不变

**是的。** 验证通过 Test 21：
- `bad["max_send_count"] = 2`（注入）
- 调用 `validate_and_apply_policy(bad)` 后
- `bad["max_send_count"]` 仍为 `2`
- `bad` 与调用前的 `raw_snapshot` 完全一致
- 只有 `receipt.effective_data["max_send_count"]` 为 `1`

所有 sanitization 和 policy 调整都在 `copy.deepcopy(manifest)` 上进行，原 manifest 不受影响。

## 5. Flexible Payload 如何清洗/转义

清洗流程（按顺序）：

1. **类型转换**: 非 str → str
2. **移除控制字符**: `remove_control_chars()`（Unicode category C，保留 \n \r \t）
3. **parse_mode 转义**: 先转义（因为转义会扩展字符），后截断
   - HTML: `escape_html()` — `&` `→` `&amp;`, `<` `→` `&lt;`, `>` `→` `&gt;`
   - MarkdownV2: `escape_markdown_v2()` — 转义 `_ * [ ] ( ) ~ \` > # + - = | { } . !` 共 18 个特殊字符
   - PlainText / 无法识别: 移除 HTML 标签 `<>`，替换 `_ * \`` 为空格，`[]` 为括号
4. **截断**: token_name≤32, symbol≤16, wallet_short≤24, extra_context≤280
5. **extra_context**: 若为 dict，先 `json.dumps` 再清洗截断

## 6. 是否可以进入 v1.9B FakeTransport / TGTransport 替换验证

**可以。** v1.9A-S2 收口补丁已完成，所有 27 个测试通过（0 失败）。

v1.9B 就绪条件：
- [x] schema_version 进入 Strict Core
- [x] Runtime Source 相对路径 + 白名单约束
- [x] 类型 + 值域边界校验（blocked/bool, leak_count/int≥0, full_address_count/int≥0, max_send_count/int≥1）
- [x] PolicyReceipt 机制（errors 阻断, adjusted_fields → effective_data）
- [x] raw_manifest 不被原地修改
- [x] Flexible Payload sanitization（截断 + 控制字符移除 + parse_mode 转义）
- [x] parse_mode / target_type 标准化（支持 legacy 中文名映射）
- [x] 全量测试通过（27/27）

v1.9B 建议：
1. 接入 FakeTransport（mock HTTP endpoint，target_type=fake/test_group）
2. 使用 `validate_and_apply_policy()` 返回的 `effective_data` 作为 Transport 输入
3. TGTransport 实现时，token/chat_id 作为 Flexible Payload 新增字段（不影响现有逻辑）
4. 端到端 fake-send 测试

## 文件变更总结

| 文件 | 变更 |
|---|---|
| `schemas/market_radar_v19.json` | +schema_version (Strict Core), +runtime_source_fields, +runtime_source_allowed_prefixes, 更新 enum 值 |
| `results/market_radar_v19_manifest_sample.json` | +schema_version, target_type → "group" (canonical) |
| `scripts/market_radar_sender.py` | +PolicyReceipt, +validate_runtime_source_paths, +validate_types_and_ranges, +sanitize_flexible_payload, +apply_policy, +validate_and_apply_policy, +normalize_parse_mode, +normalize_target_type, +escape_html, +escape_markdown_v2, +sanitize_for_parse_mode, +remove_control_chars |
| `scripts/test_market_radar_sender_v19a.py` | +11 S2 tests (共 27 测试), 更新 schema_version/target_type 检查 |
| `docs/market_radar_sender_v19a.md` | 完整 S2 文档更新 |

## 安全确认

| 检查项 | 状态 |
|---|---|
| TG API 调用 | 否 |
| 消息发送 | 否 |
| Loop/Daemon/定时任务 | 否 |
| 付费 API | 否 |
| Token/Key/Cookie 打印 | 否 |
| 远程 DB 写入 | 否 |
| 文件删除 | 否 |
| raw_manifest 原地修改 | 否 |
