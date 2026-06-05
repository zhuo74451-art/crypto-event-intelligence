# Market Radar v1.10-C — Signal Trust Gate Handoff

Generated: 2026-06-04 15:57:40 UTC+8
Task ID: 20260604_154132.r01
Run ID: 20260604_154132
Status: gate_passed
result_source: claude_code_executor
gate_version: v1.10-c
executor_lane: 1
project_label: market_radar

---

## 1. Gate Check Summary

| Field | Value |
|-------|-------|
| Gate 是否实现 | 是 |
| 是否接入发送前检查 | 是 |
| Gate 接入位置 | render_card_payload(signal) 之后、TG send 之前 |
| 是否修改 live fetch | 否 |
| 是否真实发送 TG | 否 (ACTUALLY_SEND_TG=False) |
| 是否启动后台循环 | 否 |
| 是否使用付费 API | 否 |
| 是否读取/打印密钥 | 否 |

## 2. Gate Result

| Field | Value |
|-------|-------|
| allowed | True |
| source_type | api |
| signal_type | market_anomaly |
| signal_hash | 1d1b38acc67d3ef7 |
| ttl_seconds | 900 |
| age_seconds | 810 |
| blocked_reason | None |
| target_env | test |
| checked_at | 2026-06-04T07:57:40Z |

## 3. Signal Info

| Field | Value |
|-------|-------|
| asset | SOL |
| source | hyperliquid |
| card_type | market_anomaly |

## 4. Source Trust Map Summary

| source_type | allow_test_send | allow_prod_send |
|-------------|-----------------|-----------------|
| api | True | True |
| real | True | True |
| external | True | True |
| fixture | True | False |
| manual | True | False |
| unknown | False | False |
| stale | False | False |

## 5. TTL Rules Summary

| signal_type | ttl_seconds |
|-------------|-------------|
| market_anomaly | 900 (15 min) |
| whale / whale_transfer | 3600 (60 min) |
| onchain / onchain_position | 3600 (60 min) |
| news / news_event | 21600 (6 hours) |
| macro | 21600 (6 hours) |
| position | 1800 (30 min) |
| liquidation | 1800 (30 min) |
| combo | 1800 (30 min) |
| risk_alert | 900 (15 min) |
| unknown | 0 (block immediately) |

## 6. Blocked Report

- Path: runs/market_radar/v110c_signal_trust_gate_blocked_report.jsonl
- Fields: gate_version, signal_id, signal_hash, signal_type, source_type, generated_at, checked_at, ttl_seconds, age_seconds, blocked_reason, target_env
- No token/key/cookie/password/chat_id in report

## 7. Card Text Preview (max 300 chars)

```
📉 行情异动｜SOL 下跌

一句话：SOL 24h 跌幅 7\.24% 触发行情异动监测

● 币种：SOL
● 涨跌幅：\-7\.24%
● Funding：\+0\.00%（年化 0\.1%）
● 清算情况：OI: 2\.78 亿美元，24h成交量: 5\.27 亿美元
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/solana\) / \[DexScreener\]\(https://dexscreener\.com/search?q\=SOL\)
📎 原始来源：\
```

---

## 8. Unfinished Items / Risks

- None — gate passed successfully.
- TG send was NOT attempted (v1.10-C is gate verification only).
- Next step (v1.10-D): re-enable TG send with gate active.
- No live fetch modified. No sender refactored.

---

⚠️ 仅供观察，不构成交易建议。
