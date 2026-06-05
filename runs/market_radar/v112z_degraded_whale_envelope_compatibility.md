# Market Radar v1.12-Z — Degraded Whale Envelope Compatibility Report

**Generated**: 2026-06-05 05:49:41 UTC+8
**Version**: v112Z
**Run ID**: 20260605_022952
**Based on**: v112Y degraded whale replay records

---

## 概述

本报告证明 v112Y 生成的 10 条 degraded whale replay records
已成功接入 v112H unified signal envelope 兼容层。
所有 envelope 均保留 degraded 信息，不丢失 quality flags、label confidence、
liquidation_price note、delta status 和 timestamp status。

本轮只做 envelope compatibility，不进入 TG send，不写 prod state，不调用外部 API。

## 全局统计

| 指标 | 值 |
|------|-----|
| 输入 records 数量 | 10 |
| 输出 envelopes 数量 | 10 |
| envelopes 与 records 一致 | True |
| unique_addresses | 4 |
| external_api_called | False |
| degraded_compatible | True |
| mock_replay_only | True |
| eligible_for_real_send_count | 0 |
| real_send_candidate_count | 0 |
| preview_allowed_count | 0 |
| tg_send_allowed_count | 0 |
| prod_state_write | False |
| daemon_started | False |
| watcher_started | False |
| credentials_read | False |
| files_deleted | False |

---

## Label Confidence 分布

| 置信度 | 数量 |
|--------|------|
| high | 0 |
| medium | 8 |
| low | 2 |
| unknown | 0 |

**注意**: 没有 high confidence 标签。所有标签均为 medium 或 low。
low-confidence / unknown whale 未伪装成确定机构。

---

## Quality Flags 分布

| Flag | 出现次数 |
|------|----------|
| degraded_label_confidence | 10 |
| delta_unavailable | 10 |
| liquidation_price_missing | 7 |
| local_timestamp_only | 10 |

---

## 降级信息保留状态

| 字段 | 保留状态 |
|------|----------|
| quality_flags | ✅ 已保留 |
| label_confidence | ✅ 已保留 |
| liquidation_price_note | ✅ 已保留 |
| delta_status | ✅ 已保留 |
| timestamp_status | ✅ 已保留 |

---

## Routing Guard 状态

| Guard | 值 |
|-------|-----|
| preview_allowed | false |
| tg_send_allowed | false |
| prod_state_write_allowed | false |

**所有 envelope 均**:
- eligible_for_real_send = false
- real_send_candidate = false
- 不得进入 TG send path
- 不伪装成 live passed

---

## Envelope 列表

### 1. ETH long — Matrixport Related

| 字段 | 值 |
|------|-----|
| address | `0x6c85...84f6` |
| label | Matrixport Related |
| label_confidence | medium |
| label_explanation | Label 'Matrixport Related' (entity_type=fund_wallet) has medium confidence: Enti... |
| asset | ETH |
| side | long |
| notional_usd | 70,796,000 |
| entry_price | 2,265.44 |
| liquidation_price | 1365.991167 |
| liquidation_price_note | 清算价格可用：1365.991167. HyperLiquid cross-margin position return... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 3 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 2. WLD long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | WLD |
| side | long |
| notional_usd | 5,016,032 |
| entry_price | 0.51 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 3. TON long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | TON |
| side | long |
| notional_usd | 3,214,681 |
| entry_price | 1.87 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 4. NEAR long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | NEAR |
| side | long |
| notional_usd | 2,048,335 |
| entry_price | 2.77 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 5. HYPE long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | HYPE |
| side | long |
| notional_usd | 8,985,122 |
| entry_price | 70.54 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 6. ASTER long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | ASTER |
| side | long |
| notional_usd | 2,352,762 |
| entry_price | 0.74 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 7. ZEC long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | ZEC |
| side | long |
| notional_usd | 4,496,062 |
| entry_price | 543.62 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 8. XMR long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| label_explanation | Label 'loraclexyz' (entity_type=high_leverage_trader) has medium confidence: Ent... |
| asset | XMR |
| side | long |
| notional_usd | 2,408,325 |
| entry_price | 336.88 |
| liquidation_price | None |
| liquidation_price_note | 清算价格不可用：HyperLiquid cross-margin position returned null liqu... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, liquidation_price_missing, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 4 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 9. HYPE long — Unknown HYPE Whale

| 字段 | 值 |
|------|-----|
| address | `0x082e...ca88` |
| label | Unknown HYPE Whale |
| label_confidence | low |
| label_explanation | Label 'Unknown HYPE Whale' (entity_type=unknown_whale) has LOW confidence: Entit... |
| asset | HYPE |
| side | long |
| notional_usd | 90,762,646 |
| entry_price | 38.68 |
| liquidation_price | 55.010805 |
| liquidation_price_note | 清算价格可用：55.010805. HyperLiquid cross-margin position returned... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 3 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

### 10. BTC short — Unknown Hyperliquid Whale

| 字段 | 值 |
|------|-----|
| address | `0x50b3...9f20` |
| label | Unknown Hyperliquid Whale |
| label_confidence | low |
| label_explanation | Label 'Unknown Hyperliquid Whale' (entity_type=unknown_whale) has LOW confidence... |
| asset | BTC |
| side | short |
| notional_usd | 14,070,276 |
| entry_price | 63,583.00 |
| liquidation_price | 86953.672441 |
| liquidation_price_note | 清算价格可用：86953.672441. HyperLiquid cross-margin position retur... |
| delta_status | unavailable_one_shot_no_previous_position |
| timestamp_status | local_observed_at_no_hl_server_timestamp |
| quality_flags | degraded_label_confidence, delta_unavailable, local_timestamp_only |
| degrade_reasons count | 3 |
| eligible_for_real_send | False |
| real_send_candidate | False |
| routing_guard.tg_send_allowed | False |

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| external_api_called | false |
| tg_send | false |
| prod_state_write | false |
| daemon_started | false |
| watcher_started | false |
| credentials_read | false |
| files_deleted | false |
| eligible_for_real_send | false (all) |
| real_send_candidate | false (all) |
| degraded 伪装成 live passed | false |

---

## 下一步建议

v113a: degraded whale preview pack local-only — 生成本地预览卡片，
但仍不进入 TG send path。
