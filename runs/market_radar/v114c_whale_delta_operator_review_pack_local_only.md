# v114C Whale Delta Operator Review Pack — Local Only

**Generated:** 2026-06-05T06:17:12.048009+08:00
**Status:** passed
**Version:** v114C

---

## 目的 (Purpose)

基于 v114B 的 10 条 whale position delta records，生成本地 operator review pack。
所有内容仅用于本地审阅，不进入 TG send，不写 prod state。

---

## v114B Delta 总览

| 指标 | 数值 |
|------|------|
| 输入 delta records | 10 |
| closed_position | 1 |
| size_changed | 5 |
| unchanged | 4 |
| new_position | 0 |

### 注意力分布

| 级别 | 数量 |
|------|------|
| 🔴 High | 1 |
| 🟡 Medium | 5 |
| 🟢 Low | 4 |

---

## 🔴 高优先级事件 (High Attention)

### BTC Short — Closed Position

| 字段 | 值 |
|------|-----|
| 地址 | `0x50b309f78e774a756a2230e1769729094cac9f20` |
| 标签 | Unknown Hyperliquid Whale |
| 标签置信度 | low |
| 资产 | BTC |
| 方向 | short |
| 基线仓位大小 | 14,070,275.76 |
| 当前仓位大小 | 0 |
| 变化量 | -14,070,275.76 |
| 操作员关注级别 | **high** |
| 审查摘要 | BTC short position disappeared in second probe; classify as closed_position for local operator review only. |

**结论：** `0x50b3...ac9f20` 的 BTC short 已从 baseline 中消失，
明确标记为 `closed_position` 和 `high_operator_attention`。

**注意：** 标签置信度为 low（"Unknown Hyperliquid Whale"），
不能伪装成确定机构。这是本地审阅分类，不是交易信号。

---

## 🟡 仓位变化表格 (Size Changed — Medium Attention)

按变化幅度（size_delta_abs）降序排列：

| Asset | Label | Confidence | Baseline Size | Current Size | Delta | Abs Delta |
|-------|-------|------------|---------------|--------------|-------|-----------|
| HYPE | Unknown HYPE Whale (0x082e843a...edca88) | low | 90,762,645.66 | 89,683,452.30 | -1,079,193.36 | 1,079,193.36 |
| ZEC | loraclexyz (0x8def9f50...992dae) | medium | 4,496,061.81 | 4,290,266.40 | -205,795.41 | 205,795.41 |
| HYPE | loraclexyz (0x8def9f50...992dae) | medium | 8,985,121.56 | 8,878,285.94 | -106,835.62 | 106,835.62 |
| TON | loraclexyz (0x8def9f50...992dae) | medium | 3,214,680.84 | 3,117,369.73 | -97,311.11 | 97,311.11 |
| WLD | loraclexyz (0x8def9f50...992dae) | medium | 5,016,032.37 | 4,946,543.25 | -69,489.12 | 69,489.12 |

---

## 🟢 低优先级观察区 (Unchanged — Low Attention)

| Asset | Label | Confidence | Side | Current Size |
|-------|-------|------------|------|--------------|
| ETH | Matrixport Related (0x6c851251...fd84f6) | medium | long | 70,360,000.00 |
| NEAR | loraclexyz (0x8def9f50...992dae) | medium | long | 2,029,861.38 |
| XMR | loraclexyz (0x8def9f50...992dae) | medium | long | 2,421,168.27 |
| ASTER | loraclexyz (0x8def9f50...992dae) | medium | long | 2,342,259.41 |

---

## Label Confidence 摘要

| 级别 | 数量 | 说明 |
|------|------|------|
| High | 0 | 无高置信度标签 |
| Medium | 8 | 含 loraclexyz (7) + Matrixport Related (1) |
| Low | 2 | Unknown Hyperliquid Whale + Unknown HYPE Whale |

**标注：** 所有标签置信度从 v114A baseline 保留，本轮未升级。

---

## Liquidation Price 可用性

| 状态 | 数量 |
|------|------|
| 可用 | 3 |
| 缺失 / null | 7 |

---

## 安全不变量摘要 (Safety Invariant Summary)

| Address | Asset | Side | Delta Type | Attention | local_review_only | operator_action | eligible_for_real_send | tg_send_allowed | prod_state_write |
|---------|-------|------|------------|-----------|-------------------|-----------------|------------------------|-----------------|------------------|
| 0x50b309f7...ac9f20 | BTC | short | closed_position | high | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x082e843a...edca88 | HYPE | long | size_changed | medium | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | ZEC | long | size_changed | medium | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | HYPE | long | size_changed | medium | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | TON | long | size_changed | medium | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | WLD | long | size_changed | medium | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x6c851251...fd84f6 | ETH | long | unchanged | low | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | NEAR | long | unchanged | low | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | XMR | long | unchanged | low | ✅ | ✅ | ✅ | ✅ | ✅ |
| 0x8def9f50...992dae | ASTER | long | unchanged | low | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Known Data Consistency Note

**v113D historical count mismatch：**
v113D legacy test 有 `total_positions_found=9` vs v114A baseline=10。
这是已知历史字段不一致（v112X 同一批数据的不同快照时点造成）。
本轮 v114C 不修改旧 seal，只记录此已知差异。
不影响 v114B delta records 的本地 review pack。

---

## 明确结论

| 结论 | 状态 |
|------|------|
| local_operator_review_only | ✅ True |
| not_tg_send_ready | ✅ 确认 (所有 cards tg_send_allowed=false) |
| not_prod_state_ready | ✅ 确认 (prod_state_write=false) |
| not_real_send_candidate | ✅ 确认 (eligible_for_real_send_count=0) |
| external_api_called | ✅ False |
| credentials_read | ✅ False |
| daemon_started | ✅ False |
| watcher_started | ✅ False |
| files_deleted | ✅ False |

---

## 下一步建议

**v114D:** Whale delta review pack seal — local-only。
- 对本轮 operator review cards 做最终 seal
- 确认所有分类和审查摘要
- 不进入 TG send，不写 prod state

---

## 输出文件

| 文件 | 路径 |
|------|------|
| Result JSON | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114c_whale_delta_operator_review_pack_result.json` |
| Review Cards JSONL | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114c_whale_delta_operator_review_cards.jsonl` |
| Report MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v114c_whale_delta_operator_review_pack_local_only.md` |
| Handoff MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v114c_whale_delta_operator_review_pack_local_only_handoff.md` |

---

*本报告仅用于本地运营审阅。不构成交易建议，不自动发送。*
