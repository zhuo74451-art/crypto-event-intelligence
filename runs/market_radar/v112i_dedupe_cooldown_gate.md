# Market Radar v1.12-I — Dedupe + Cooldown Gate Report

**Generated**: 2026-06-05 04:13:19 UTC+8
**Version**: v1.12-I
**Run ID**: 20260604_202718
**Schema Version**: 1.0.0

---

## 概述

本报告证明 Dedupe + Cooldown Gate 层已建立，接收 v112h 统一 Signal Envelope，
执行去重和冷却检查，输出 gate decision。

每条 envelope 经过：
1. **Dedupe check** — 检查 dedupe_key 是否已存在于 prior state
2. **Cooldown check** — 检查 cooldown_key 是否在冷却期内
3. **Leak scan** — 检查 decision 输出中是否有泄漏

本任务未连接外部 API、未发送 TG、未启动 daemon/loop/cron。

## 全局统计

| 指标 | 值 |
|------|-----|
| input_envelope_count | 13 |
| decision_count | 13 |
| passed_count | 9 |
| blocked_dedupe_count | 2 |
| blocked_cooldown_count | 2 |
| blocked_invalid_count | 0 |
| blocked_leak_count | 0 |
| eligible_for_send_count | 9 |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| decision_count_matches_input | True |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |
| live_ready | False |

---

## Cooldown Policy

| Card Type | Cooldown (min) |
|-----------|---------------|
| `price_oi_volume_anomaly` | 60 |
| `whale_position_alert` | 90 |
| `liquidation_pressure` | 30 |
| `multi_asset_market_sync` | 45 |
| `news_event_market_impact` | 120 |

---

## Card Type Summary

| Card Type | Total | Pass | Dedupe | Cooldown | Invalid | Leak |
|-----------|-------|------|--------|----------|---------|------|
| `liquidation_pressure` | 3 | 2 | 0 | 1 | 0 | 0 |
| `multi_asset_market_sync` | 3 | 3 | 0 | 0 | 0 | 0 |
| `news_event_market_impact` | 3 | 2 | 0 | 1 | 0 | 0 |
| `price_oi_volume_anomaly` | 1 | 0 | 1 | 0 | 0 | 0 |
| `whale_position_alert` | 3 | 2 | 1 | 0 | 0 | 0 |

---

## Gate Decision 列表

### 1. [DEDUPE] blocked_dedupe — `sig-pova-cf3a0c25-202606042000`

| 字段 | 值 |
|------|-----|
| card_type | price_oi_volume_anomaly |
| primary_assets | BTC |
| direction | bullish |
| gate_status | blocked_dedupe |
| dedupe_hit | True |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | False |
| observed_at | 2026-06-04T20:00:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- dedupe_key already exists in prior state: 8b7c4239a2b7ee3d...

### 2. [PASS] pass — `sig-wpa-f71d2b1d-202606041945`

| 字段 | 值 |
|------|-----|
| card_type | whale_position_alert |
| primary_assets | BTC |
| direction | bullish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T19:45:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 3. [DEDUPE] blocked_dedupe — `sig-wpa-1ae7a01d-202606042010`

| 字段 | 值 |
|------|-----|
| card_type | whale_position_alert |
| primary_assets | ETH |
| direction | bearish |
| gate_status | blocked_dedupe |
| dedupe_hit | True |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | False |
| observed_at | 2026-06-04T20:10:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- dedupe_key already exists in prior state: c74e9e689d3257ec...

### 4. [PASS] pass — `sig-wpa-46d9d399-202606042022`

| 字段 | 值 |
|------|-----|
| card_type | whale_position_alert |
| primary_assets | SOL |
| direction | bullish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T20:22:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 5. [COOLDOWN] blocked_cooldown — `sig-lipr-a94980e2-202606041200`

| 字段 | 值 |
|------|-----|
| card_type | liquidation_pressure |
| primary_assets | BTC |
| direction | bearish |
| gate_status | blocked_cooldown |
| dedupe_hit | False |
| cooldown_hit | True |
| cooldown_until | 2026-06-04T23:45:00+08:00 |
| eligible_for_send | False |
| observed_at | 2026-06-04T12:00:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- cooldown_key hit, cooldown active until 2026-06-04T23:45:00+08:00: d62e85c889be446e...

### 6. [PASS] pass — `sig-lipr-dd740422-202606041200`

| 字段 | 值 |
|------|-----|
| card_type | liquidation_pressure |
| primary_assets | ETH |
| direction | bullish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T12:00:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 7. [PASS] pass — `sig-lipr-03ec60ab-202606041200`

| 字段 | 值 |
|------|-----|
| card_type | liquidation_pressure |
| primary_assets | SOL |
| direction | mixed |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T12:00:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 8. [PASS] pass — `sig-mams-018a768f-202606041430`

| 字段 | 值 |
|------|-----|
| card_type | multi_asset_market_sync |
| primary_assets | SOL, BTC, ETH |
| direction | bullish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T14:30:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 9. [PASS] pass — `sig-mams-a4e05c21-202606041515`

| 字段 | 值 |
|------|-----|
| card_type | multi_asset_market_sync |
| primary_assets | OP, ARB, MATIC |
| direction | bullish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T15:15:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 10. [PASS] pass — `sig-mams-b2ab4cdd-202606041600`

| 字段 | 值 |
|------|-----|
| card_type | multi_asset_market_sync |
| primary_assets | BNB, OKB, BGB |
| direction | bullish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | 2026-06-04T20:45:00+08:00 |
| eligible_for_send | True |
| observed_at | 2026-06-04T16:00:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- cooldown_key found but cooldown expired at 2026-06-04T20:45:00+08:00: 0ee7143b11a0ce80...
- cooldown expired — signal passes
- no active dedupe or cooldown block — signal passes

### 11. [COOLDOWN] blocked_cooldown — `sig-nemi-d3dbfd91-202606041430`

| 字段 | 值 |
|------|-----|
| card_type | news_event_market_impact |
| primary_assets | BTC |
| direction | bullish |
| gate_status | blocked_cooldown |
| dedupe_hit | False |
| cooldown_hit | True |
| cooldown_until | 2026-06-05T00:00:00+08:00 |
| eligible_for_send | False |
| observed_at | 2026-06-04T14:30:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- cooldown_key hit, cooldown active until 2026-06-05T00:00:00+08:00: 2e7268b07cb27896...

### 12. [PASS] pass — `sig-nemi-f8590f16-202606041015`

| 字段 | 值 |
|------|-----|
| card_type | news_event_market_impact |
| primary_assets | DEFI, ETH |
| direction | bearish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T10:15:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

### 13. [PASS] pass — `sig-nemi-20d248d1-202606040845`

| 字段 | 值 |
|------|-----|
| card_type | news_event_market_impact |
| primary_assets | ARB, ETH, USDC |
| direction | bearish |
| gate_status | pass |
| dedupe_hit | False |
| cooldown_hit | False |
| cooldown_until | N/A |
| eligible_for_send | True |
| observed_at | 2026-06-04T08:45:00+08:00 |
| evaluated_at | 2026-06-04T22:30:00+08:00 |

**Gate Reasons**:

- no active dedupe or cooldown block — signal passes

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| real_tg_sent | false |
| external_api_called | false |
| external_ai_called | false |
| daemon_started | false |
| live_ready | false |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| files_deleted | false |
