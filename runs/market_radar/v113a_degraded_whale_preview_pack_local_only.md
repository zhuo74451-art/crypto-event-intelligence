# Market Radar v1.13-A — Degraded Whale Preview Pack (Local Only) 报告

**Generated**: 2026-06-05 05:56:54 UTC+8
**Version**: v113A
**Run ID**: 20260605_022952
**Task ID**: 20260605_v113a_degraded_whale_preview_pack_local_only
**Based on**: v112Z degraded whale envelopes

---

## 概述

本报告证明基于 v112Z 的 10 条 degraded whale envelopes
成功生成了 10 张本地 preview card。

所有 preview card 均保留 degraded 标识，用于验证 Market Radar 卡片展示层
能正确表达降级状态。本轮**仅生成本地预览包**，不做 TG 发送，不做外部请求，
不做生产写入。

---

## 全局统计

| 指标 | 值 |
|------|-----|
| 输入 envelopes 数量 | 10 |
| 输出 preview cards 数量 | 10 |
| cards 与 envelopes 一致 | True |
| external_api_called | False |
| local_preview_only | True |
| degraded_preview_pack_built | True |
| eligible_for_real_send_count | 0 |
| real_send_candidate_count | 0 |
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

**注意**: 没有 high confidence 标签。low/medium 标签均保留 label_explanation，
未伪装成确定机构。

---

## Warnings 分布

| Warning | 出现次数 |
|---------|----------|
| 使用本地观察时间，非 HyperLiquid 服务端时间 | 10 |
| 单次快照，暂无法计算仓位变化 | 10 |
| 标签置信度不足 | 10 |
| 清算价格不可用 | 7 |

---

## Degraded 展示层验证状态

| 展示项 | 状态 |
|--------|------|
| label_confidence_displayed | ✅ |
| liquidation_price_unavailable_displayed | ✅ |
| delta_unavailable_displayed | ✅ |
| local_timestamp_displayed | ✅ |

---

## Routing Guard 状态

| Guard | 值 |
|-------|-----|
| local_preview_only | true (all) |
| eligible_for_real_send | false (all) |
| real_send_candidate | false (all) |
| tg_send_allowed | false (all) |
| prod_state_write_allowed | false (all) |

**所有 preview card 均**:
- local_preview_only = true
- eligible_for_real_send = false
- real_send_candidate = false
- tg_send_allowed = false
- 不得进入 TG send path
- 不伪装成 live passed
- 不写 prod state

---

## Preview Card 列表

### 1. ETH long — Matrixport Related

| 字段 | 值 |
|------|-----|
| address | `0x6c85...84f6` |
| label | Matrixport Related |
| label_confidence | medium |
| entity_type | fund_wallet |
| asset | ETH |
| side | long |
| notional_usd | 70,796,000 |
| leverage | 20x |
| liquidation_price_display | $1,365.99 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 2. WLD long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | WLD |
| side | long |
| notional_usd | 5,016,032 |
| leverage | 10x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 3. TON long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | TON |
| side | long |
| notional_usd | 3,214,681 |
| leverage | 5x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 4. NEAR long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | NEAR |
| side | long |
| notional_usd | 2,048,335 |
| leverage | 10x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 5. HYPE long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | HYPE |
| side | long |
| notional_usd | 8,985,122 |
| leverage | 2x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 6. ASTER long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | ASTER |
| side | long |
| notional_usd | 2,352,762 |
| leverage | 5x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 7. ZEC long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | ZEC |
| side | long |
| notional_usd | 4,496,062 |
| leverage | 10x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 8. XMR long — loraclexyz

| 字段 | 值 |
|------|-----|
| address | `0x8def...2dae` |
| label | loraclexyz |
| label_confidence | medium |
| entity_type | high_leverage_trader |
| asset | XMR |
| side | long |
| notional_usd | 2,408,325 |
| leverage | 5x |
| liquidation_price_display | 清算价格不可用 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 清算价格不可用, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 9. HYPE long — Unknown HYPE Whale

| 字段 | 值 |
|------|-----|
| address | `0x082e...ca88` |
| label | Unknown HYPE Whale |
| label_confidence | low |
| entity_type | unknown_whale |
| asset | HYPE |
| side | long |
| notional_usd | 90,762,646 |
| leverage | 5x |
| liquidation_price_display | $55.01 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

### 10. BTC short — Unknown Hyperliquid Whale

| 字段 | 值 |
|------|-----|
| address | `0x50b3...9f20` |
| label | Unknown Hyperliquid Whale |
| label_confidence | low |
| entity_type | unknown_whale |
| asset | BTC |
| side | short |
| notional_usd | 14,070,276 |
| leverage | 20x |
| liquidation_price_display | $86,953.67 |
| delta_display | 单次快照，暂无法计算仓位变化 |
| timestamp_display | 本地观察时间 |
| local_preview_only | True |
| eligible_for_real_send | False |
| tg_send_allowed | False |
| warnings | 标签置信度不足, 单次快照，暂无法计算仓位变化, 使用本地观察时间，非 HyperLiquid 服务端时间 |

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| external_api_called | false |
| AI/API/model calls | false |
| tg_send | false |
| prod_state_write | false |
| daemon_started | false |
| watcher_started | false |
| credentials_read | false |
| files_deleted | false |
| eligible_for_real_send | false (all) |
| real_send_candidate | false (all) |
| tg_send_allowed | false (all) |
| degraded 伪装成 live passed | false |
| low-confidence 伪装成确定机构 | false |

---

## 下一步建议

v113b: degraded whale preview quality gate local-only — 
对 preview card 质量建立关卡验证，确保展示层完整覆盖降级场景。
