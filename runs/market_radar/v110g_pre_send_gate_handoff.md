# Market Radar v1.10-G — pre_send_gate 通用发送前安全接口 Handoff

Generated: 2026-06-04 16:25:22 UTC+8
Status: done
result_source: claude_code_executor
task_id: 20260604_162516.r01
executor_lane: 1
project_label: market_radar
gate_version: v1.10-c (SignalTrustGate)
pre_send_gate_version: v1.10-G

---

## 1. Summary

| Field | Value |
|-------|-------|
| pre_send_gate 是否实现 | ✅ 是 |
| v1.10-E 是否接入 | ✅ 是 |
| v1.10-F 是否接入 | ✅ 是 |
| 是否真实发送 TG | ❌ 否（本轮未真实发送） |
| 是否发正式频道 | ❌ 否 |
| 是否启动后台循环 | ❌ 否 |
| 是否使用付费 API | ❌ 否 |
| 是否读取/打印密钥 | ❌ 否 |
| 是否删除文件 | ❌ 否 |

## 2. Modified Files

| File | Change |
|------|--------|
| `scripts/market_radar_pre_send_gate.py` | **新增** — 通用 `pre_send_gate()` 接口 |
| `scripts/test_market_radar_pre_send_gate_v110g.py` | **新增** — 16 个单元测试 |
| `scripts/_v110e_gate_protected_test_channel_send.py` | **修改** — Step 3 从 inline `SignalTrustGate.check()` 改为调用 `pre_send_gate()` |
| `scripts/_v110f_gate_protected_test_channel_matrix_send.py` | **修改** — Step 3b 循环内从 inline `gate.check()` 改为调用 `pre_send_gate()` |

## 3. Commands Executed

```bash
python scripts/test_market_radar_pre_send_gate_v110g.py
python scripts/test_market_radar_signal_trust_gate_v110c.py
python scripts/test_market_radar_card_router_v110a.py
```

## 4. Test Results

| Test Suite | Result |
|------------|--------|
| v1.10-G pre_send_gate tests | **16/16 passed** |
| v1.10-C SignalTrustGate tests | **26/26 passed** |
| v1.10-A Card Router tests | **28/28 passed** |

### v1.10-G Test Cases Verified

| # | Test Case | Result |
|---|-----------|--------|
| 1 | fresh api signal + valid payload + test → allowed=True | ✅ |
| 2 | fixture + valid payload + test → allowed=True | ✅ |
| 3 | fixture + valid payload + prod → allowed=False | ✅ |
| 4 | unknown source_type → allowed=False | ✅ |
| 5 | expired signal → allowed=False | ✅ |
| 6 | missing payload text → allowed=False | ✅ |
| 7 | empty payload text → allowed=False | ✅ |
| 8 | parse_mode=None but text valid → allowed=True | ✅ |
| 9 | blocked result 包含 signal_hash | ✅ |
| 10 | 不包含 token/chat_id/key 敏感字段 | ✅ |
| 11 | allowed result structure (all required keys) | ✅ |
| 12 | blocked result structure (blocked_reason non-empty) | ✅ |
| 13 | gate blocked but payload valid → allowed=False, payload_ok=True | ✅ |
| 14 | both gate blocked and payload bad → allowed=False, payload_ok=False | ✅ |
| 15 | signal_hash deterministic across calls | ✅ |
| 16 | default target_env=test | ✅ |

## 5. pre_send_gate 接口设计

### 函数签名

```python
def pre_send_gate(signal: dict, payload: dict, target_env: str = "test") -> dict:
```

### 返回结构

```python
{
    "allowed": True | False,       # True only if BOTH gate check AND payload check pass
    "target_env": "test" | "prod",
    "gate_result": {...},          # Full SignalTrustGate.check() result
    "payload_ok": True | False,    # Payload text non-empty and parse_mode present
    "blocked_reason": None | "...",# Why it was blocked (None if allowed)
    "signal_hash": "...",          # Deterministic 16-char hash
    "gate_version": "v1.10-c",
}
```

### 检查逻辑

1. 调用 `SignalTrustGate().check(signal, target_env=target_env)` — 来源信任 + TTL + 信号合法性
2. 检查 payload 是否为 dict
3. 检查 payload 是否包含 `text`
4. 检查 payload text 是否非空
5. 检查 payload 是否包含 `parse_mode`
6. 综合 gate_result + payload checks → `allowed` 判定

### 安全边界

- ✅ 不读取环境变量中的 token/chat_id/key
- ✅ 不做网络调用
- ✅ 不打印/保存任何密钥
- ✅ 返回结果中不含 token/chat_id/key/cookie/password 等敏感字段

## 6. v1.10-E 接入详情

原代码：
```python
gate = SignalTrustGate()
gate_result = gate.check(selected, target_env=TARGET_ENV)
gate_blocked = not gate_result["allowed"]
```

现代码：
```python
precheck = pre_send_gate(selected, payload, target_env=TARGET_ENV)
gate_result = precheck["gate_result"]
gate_blocked = not precheck["allowed"]
```

改动范围：
- 新增 `from scripts.market_radar_pre_send_gate import pre_send_gate`
- Step 3 从 "SignalTrustGate check" 改为 "pre_send_gate() universal check"
- 多了一层 payload 校验（payload_ok 字段）
- component_chain 更新

## 7. v1.10-F 接入详情

原代码（循环内每信号）：
```python
gate = SignalTrustGate()  # 创建于循环外
gate_result = gate.check(signal, target_env=TARGET_ENV)
gate_allowed = gate_result["allowed"]
```

现代码（循环内每信号）：
```python
precheck = pre_send_gate(signal, payload, target_env=TARGET_ENV)
gate_result = precheck["gate_result"]
gate_allowed = precheck["allowed"]
```

改动范围：
- 新增 `from scripts.market_radar_pre_send_gate import pre_send_gate`
- 移除循环外的 `gate = SignalTrustGate()`（pre_send_gate 内部自行创建）
- Step 3b 从 "Gate check" 改为 "pre_send_gate() universal check"
- 多了 payload_ok 打印
- block_reason 使用 precheck 的统一 blocked_reason
- 在 send_results 中使用了 precheck["signal_hash"]

## 8. 未修改项

| 组件 | 说明 |
|------|------|
| `SignalTrustGate` 类 | 未改动 |
| `render_card_payload()` | 未改动 |
| `TGTransport` | 未改动 |
| `MarketRadarSender` | 未改动 |
| `market_radar_sender.py` | 未改动 |
| `market_radar_card_router.py` | 未改动 |
| `market_radar_free_sources.py` | 未改动 |
| `market_radar_tg_formatting.py` | 未改动 |
| 数据源 / RSS trust map | 未扩展 |
| 生产频道配置 | 未改动 |

## 9. Acceptance Checklist

| Item | Status |
|------|--------|
| pre_send_gate() 已实现 | ✅ |
| v1.10-E 改为调用 pre_send_gate() | ✅ |
| v1.10-F 改为调用 pre_send_gate() | ✅ |
| 所有新测试通过 (16/16) | ✅ |
| v1.10-C Gate 测试仍通过 (26/26) | ✅ |
| v1.10-A Card Router 测试仍通过 (28/28) | ✅ |
| 本轮没有真实发送 TG | ✅ |
| 没有泄露密钥 | ✅ |
| 没有启动后台循环 | ✅ |
| 没有调用付费 API | ✅ |
| 没有删除文件 | ✅ |
| 没有新增数据源 | ✅ |

## 10. Unfinished Items / Risks

- None — pre_send_gate() 接口抽象完成，v1.10-E / v1.10-F 均已接入。
- 未来合并 v1.10-E 和 v1.10-F 中仍存在的重复发送流程时，pre_send_gate() 可作为统一入口。
- 如新增 sender（如 address_behavior_card / daily digest），应使用 pre_send_gate() 而非直接调 SignalTrustGate。

## 11. Next Steps

1. **v1.10-H**: 将 pre_send_gate() 接入所有现有 TG sender（如 `send_address_behavior_card_gate.py`、`send_tg_market_radar_board.py` 等），确保无一遗漏。
2. **v1.10-I**: 测试频道 5-10 条真实信号稳定性回放，验证 pre_send_gate() 在 real signal flow 下的表现。
3. 如 live fetch 持续出现数据源不稳定，可在 pre_send_gate() 层面增加 signal freshness 的额外告警（不阻塞发送，仅记录）。

---
⚠️ 仅供观察，不构成交易建议。
