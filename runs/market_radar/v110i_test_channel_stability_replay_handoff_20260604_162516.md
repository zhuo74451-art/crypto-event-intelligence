# Market Radar v1.10-I — Test Channel Stability Replay Handoff

Generated: 2026-06-04 16:44:34 UTC+8
Task ID: 20260604_162516.r03
Run ID: 20260604_162516
Status: done
result_source: claude_code_executor
executor_lane: 1
project_label: market_radar
gate_version: v1.10-c

---

## 1. Send Summary

| Field | Value |
|-------|-------|
| 是否真实发送 TG | 是 |
| 是否测试频道 | 是 |
| 是否正式频道 | 否 |
| target_env | test |
| max_send_count | 5 |
| planned_send_count | 3 |
| actual_sent_count | 3 |
| gate_blocked_count | 0 |
| message_ids | ["2257", "2258", "2259"] |
| status_codes | [200, 200, 200] |
| fallback_used_count | 0 |
| parse_modes | ["MarkdownV2", "MarkdownV2", "MarkdownV2"] |
| 是否启动后台循环 | 否 |
| 是否使用付费 API | 否 |
| 是否读取/打印密钥 | 否 |
| 是否泄露 token/chat_id | 否 |
| secrets_loaded_via | .\scripts\load_local_secrets.ps1 |

## 2. Gate Results Summary

| # | Asset | Signal Type | Source Type | Gate Allowed | Blocked Reason |
|---|-------|-------------|-------------|-------------|----------------|
| 1 | ARB | market_anomaly | api | True | N/A |
| 2 | SUI | market_anomaly | api | True | N/A |
| 3 | BTC | market_anomaly | api | True | N/A |

## 3. Send Details

### Card 1: ARB

| Field | Value |
|-------|-------|
| signal_type | market_anomaly |
| source_type | api |
| card_type | market_anomaly |
| gate_allowed | True |
| sent | True |
| message_id | 2257 |
| status_code | 200 |
| fallback_used | False |
| parse_mode_final | MarkdownV2 |
| attempts | 1 |
| error_type |  |
| error_message |  |

### Card 2: SUI

| Field | Value |
|-------|-------|
| signal_type | market_anomaly |
| source_type | api |
| card_type | market_anomaly |
| gate_allowed | True |
| sent | True |
| message_id | 2258 |
| status_code | 200 |
| fallback_used | False |
| parse_mode_final | MarkdownV2 |
| attempts | 1 |
| error_type |  |
| error_message |  |

### Card 3: BTC

| Field | Value |
|-------|-------|
| signal_type | market_anomaly |
| source_type | api |
| card_type | market_anomaly |
| gate_allowed | True |
| sent | True |
| message_id | 2259 |
| status_code | 200 |
| fallback_used | False |
| parse_mode_final | MarkdownV2 |
| attempts | 1 |
| error_type |  |
| error_message |  |

## 4. Signals Selected

Selection rules: 优先真实 live signal（api/real/external），不用 fixture；优先不同 asset；优先不同 signal_type；RSS 不加入 trust map。

| # | Asset | Signal Type | Source | Price Change | Observed At |
|---|-------|-------------|--------|-------------|-------------|
| 1 | ARB | market_anomaly | hyperliquid | -6.75 | 2026-06-04T08:42:17Z |
| 2 | SUI | market_anomaly | hyperliquid | -5.96 | 2026-06-04T08:42:17Z |
| 3 | BTC | market_anomaly | hyperliquid | -5.21 | 2026-06-04T08:42:17Z |

## 5. Blocked Signals

- None — all selected signals passed pre_send_gate check.

## 6. pre_send_gate Results (per signal)

### Signal 1: ARB

- allowed: True
- signal_hash: 8821f71d22e4947a
- age_seconds: 137
- ttl_seconds: 900
- source_type: api
- payload_ok: N/A
- blocked_reason: N/A

### Signal 2: SUI

- allowed: True
- signal_hash: 9168c91365cc6cd8
- age_seconds: 140
- ttl_seconds: 900
- source_type: api
- payload_ok: N/A
- blocked_reason: N/A

### Signal 3: BTC

- allowed: True
- signal_hash: 795e12d594f082a7
- age_seconds: 143
- ttl_seconds: 900
- source_type: api
- payload_ok: N/A
- blocked_reason: N/A

## 7. Test Verification

| Check | Result |
|-------|--------|
| pre_send_gate tests (v1.10-G) | 16/16 passed |
| SignalTrustGate tests (v1.10-C) | 26/26 passed |
| Card Router tests (v1.10-A) | 28/28 passed |
| Sender Gate Coverage tests (v1.10-H) | 15/15 passed |
| Total tests passed | 85/85 |
| Gate engaged before every send | Yes |
| Target = test channel only | Yes |
| Production channel sent | No |
| max_send_count ≤ 5 | Yes |
| All sends return real message_id | Yes |

## 8. Safety Boundary

| Constraint | Status |
|------------|--------|
| 不送正式频道 | ✅ |
| 最多发送 5 张 | ✅ |
| 不启动 loop/daemon/cron | ✅ |
| 不调用付费 API | ✅ |
| 不读取/打印/保存 token/chat_id/key | ✅ |
| 不删除文件 | ✅ |
| 不新增数据源 | ✅ |
| 不做卡片美化 | ✅ |
| 不做 RSS trust map 扩展 | ✅ |
| 不用 fixture 冒充真实信号 | ✅ |
| 不改生产频道配置 | ✅ |
| 每张发送前经过 pre_send_gate(signal, payload, target_env="test") | ✅ |

## 9. Send Text Previews (max 250 chars each, credentials redacted)

### Card 1: ARB
```
📉 行情异动｜ARB 下跌

一句话：ARB 24h 跌幅 6\.75% 触发行情异动监测

● 币种：ARB
● 涨跌幅：\-6\.75%
● Funding：\+0\.00%（年化 1\.4%）
● 清算情况：OI: 467\.10 万美元，24h成交量: 490\.57 万美元
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/arbitrum\) / \[DexScree
```

### Card 2: SUI
```
📉 行情异动｜SUI 下跌

一句话：SUI 24h 跌幅 5\.96% 触发行情异动监测

● 币种：SUI
● 涨跌幅：\-5\.96%
● Funding：\+0\.00%（年化 0\.3%）
● 清算情况：OI: 2818\.22 万美元，24h成交量: 2134\.41 万美元
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/sui\) / \[DexScreener
```

### Card 3: BTC
```
📉 行情异动｜BTC 下跌

一句话：BTC 24h 跌幅 5\.21% 触发行情异动监测

● 币种：BTC
● 涨跌幅：\-5\.21%
● Funding：\+0\.00%（年化 0\.4%）
● 清算情况：OI: 18\.80 亿美元，24h成交量: 64\.09 亿美元
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/bitcoin\) / \[DexScreener
```

---

## 10. Component Chain

```
signals (from run_market_radar_v110a_free_cards.py)
  → selection: real fresh api market_anomaly, different assets
  → render_card_payload(signal)
  → pre_send_gate(signal, payload, target_env="test") [v1.10-G universal]
  → SignalTrustGate
  → gate allowed
  → TGTransport.send(target="supergroup", parse_mode=...)
  → TG test channel real send
  → real message_id returned
```

## 11. Unfinished Items / Risks

- None — all selected signals passed gate and were sent successfully.

## 12. Summary for Gemini Review

v1.10-I Test Channel Stability Replay 执行完成。3/3 张卡片成功发送到 TG 测试频道。

- **实际发送数**: 3/3
- **Gate blocked**: 0
- **message_ids**: ["2257", "2258", "2259"]
- **Fallback 使用**: 0 次
- **85/85 测试通过**: ✅

### 给 Gemini 下一轮复核的问题

1. 如果 v1.10-I 3-5 张测试频道稳定性回放通过，是否可以标记为"测试频道安全 MVP 封口完成"？

2. 下一步应优先做 production_handoff 文档但不启用正式频道，还是继续测试频道 10 条以内回放？

3. send_tg_market_radar_board.py 这种 board-level sender 是否应该先保持禁用/只 dry-run，等有 board-level gate 再允许发送？

---
⚠️ 仅供观察，不构成交易建议。
