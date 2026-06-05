# Market Radar v1.9C — Published History JSONL Persistence Handoff

Generated: 2026-06-04 12:32:00 UTC+8
Task ID: 20260604_121532.r03
Status: done
result_source: claude_code_executor
executor_lane: 1
project_label: market_radar

---

## 1. v1.9C Success Criteria

| Criterion | Status |
|---|---|
| message_id=2195 已沉淀进 published_history.jsonl | ✅ Yes |
| raw_api_response.result.chat.id 已脱敏 | ✅ `-REDACTED_CHAT_ID` |
| raw_api_response.result.chat.title 已脱敏 | ✅ `[REDACTED]` |
| 敏感信息残留检测 | ✅ 0 violations |
| 重复运行不重复追加 | ✅ provider=telegram + message_id=2195 dedup |
| requirements.txt 锚定 requests | ✅ `requests>=2.28.0` |
| 可进入 v1.10 | ✅ Yes |

---

## 2. raw_api_response.result.chat.id 处理详情

**原始值：** `-1003977074640`（supergroup chat ID）  
**脱敏后：** `-REDACTED_CHAT_ID`（保留负号前缀，区分 itype=supergroup vs user/group/bot）

脱敏方法：
- `_deep_redact()` 递归遍历 provider_metadata
- 检测路径中包含 `chat` 且字段名为 `id` 的整数值
- 负号前缀保留（`-` → `-REDACTED_CHAT_ID`）以区分 chat 类型
- 写入前调用 `_deep_scan_sensitive()` 验证零残留

chat.title 处理：
- 原始值 `币界网官方群` → 脱敏为 `[REDACTED]`
- 不保留真实群名，target_label_redacted 字段统一为 `[REDACTED]`

---

## 3. 敏感信息残留检测

| 检测项 | 结果 |
|---|---|
| bot_token 明文 | 0 instances |
| 完整 chat_id（≥8位数字） | 0 instances |
| API URL 中的 bot token | 0 instances |
| chat.title 原始值 | 0 instances |
| 其他 token/key/cookie/password 模式 | 0 instances |

检测方法：
1. `_deep_scan_sensitive()` 递归扫描所有嵌套层级
2. 检查字段名含 `token` 且值未脱敏
3. 检查 chat.id 值未被脱敏（≥8位整数/字符串）
4. 检查字符串值匹配 bot token 格式（digits:alphanumeric_hash ≥ 32 chars）
5. 手动验证序列化 JSON 字符串不含原始敏感值

---

## 4. 幂等去重验证

| 操作 | 结果 |
|---|---|
| 首次写入 message_id=2195 | written=True, row_count=1 |
| 二次写入（same provider + message_id） | written=False, reason="Duplicate by provider=telegram + message_id=2195" |
| 三次写入 | written=False, row_count=1 (unchanged) |

去重键：
1. `provider` + `message_id`（主键）
2. `artifact_id` + `message_id`（备选键）

---

## 5. v1.10 就绪评估

| 条件 | 状态 |
|---|---|
| published_history.jsonl 持久化 | ✅ |
| 历史记录格式稳定 | ✅ |
| 脱敏规则完整 | ✅ |
| 去重机制可行 | ✅ |
| 可扩展为 TTL / Buffer 合并 | ✅ |

**可以进入 v1.10** — TTL 过期清理、多轮更新去重、Buffer 批量写入合并设计。

---

## 6. 新增/修改文件

### 新增
- `scripts/market_radar_history.py` — 历史记录构建、脱敏、写入、去重模块
- `scripts/test_market_radar_history_v19c.py` — 11 项测试
- `data/market_radar/published_history.jsonl` — 结构化历史资产库（1 条记录）
- `results/market_radar_v19c_history_test_report.md` — 测试报告
- `runs/market_radar/v19c_published_history_handoff.md` — 本 handoff
- `runs/market_radar/v19c_published_history_handoff_20260604_121532.md` — 时间戳副本

### 修改
- `requirements.txt` — `requests` → `requests>=2.28.0`
- `docs/market_radar_sender_v19a.md` — 追加 v1.9C 章节

---

## 7. Unfinished Items / Risks

- None. v1.9C scope fully complete.
- Warning: `published_history.jsonl` is a local file asset. Incremental backup recommended before v1.10 batch operations.
