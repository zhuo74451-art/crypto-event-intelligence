# Market Radar v1.11-B — Signal Value Gate Handoff

**result_source**: `claude_code_executor`
**task_id**: `20260604_162516.r06`
**run_id**: `20260604_162516`
**status**: `done`
**generated_at**: `2026-06-04 17:08:00 UTC+8`
**executor_lane**: `1`
**project_label**: `market_radar`

---

## 1. 执行摘要

v1.11-B Multi-Factor Signal Value Gate（多因子信号价值门控）已完成实现、测试和 dry-run 验证。

基于 v1.11-A 复盘结论，实现了纯确定性规则的多因子准入门控，解决了"market_anomaly 仅因价格波动就进入发送候选"的核心问题。

**核心成果：SignalValueGate 已可用，allow/observe/block 三层决策已通过 18 个单元测试验证。**

---

## 2. 修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/market_radar_signal_value_gate_v111b.py` | 新增 | SignalValueGate 实现（evaluate_signal_value） |
| `scripts/test_market_radar_signal_value_gate_v111b.py` | 新增 | 18 个单元测试 |
| `scripts/run_market_radar_signal_value_gate_v111b_dryrun.py` | 新增 | 独立 dry-run 脚本 |
| `results/market_radar_v111b_signal_value_gate_dryrun.json` | 新增 | dry-run 结果 |
| `runs/market_radar/v111b_signal_value_gate_handoff.md` | 新增 | 本 handoff |

**未修改任何现有文件，未删除任何文件。**

---

## 3. 命令执行

| 命令 | 结果 |
|------|------|
| `python scripts/test_market_radar_signal_value_gate_v111b.py` | 18/18 passed |
| `python scripts/test_market_radar_pre_send_gate_v110g.py` | 16/16 passed |
| `python scripts/test_market_radar_signal_trust_gate_v110c.py` | 26/26 passed |
| `python scripts/test_market_radar_card_router_v110a.py` | 28/28 passed |
| `python scripts/test_market_radar_sender_gate_coverage_v110h.py` | 15/15 passed |
| `python scripts/run_market_radar_signal_value_gate_v111b_dryrun.py --no-live` | dry-run 成功 |

---

## 4. 测试结果

| 测试套件 | 通过/总计 | 状态 |
|----------|----------|------|
| v111b SignalValueGate | 18/18 | ✅ |
| v110g pre_send_gate | 16/16 | ✅ |
| v110c signal_trust_gate | 26/26 | ✅ |
| v110a card_router | 28/28 | ✅ |
| v110h sender_gate_coverage | 15/15 | ✅ |
| **合计** | **103/103** | ✅ |

**旧测试 85/85 仍通过** ✅

---

## 5. dry-run 结果

**路径**: `results/market_radar_v111b_signal_value_gate_dryrun.json`

| 指标 | 值 |
|------|-----|
| total_signals | 8 |
| allow_count | 6 (BTC, ETH, SOL, ARB, SUI, HYPE) |
| observe_count | 0 |
| block_count | 2 (LINK, DOT) |

---

## 6. SignalValueGate 规则摘要

### 因子检测

| 因子 | 触发条件 | 分值 |
|------|---------|------|
| price_move | abs(price_change_pct) >= 5% | +30 |
| strong_price_move | abs(price_change_pct) >= 8% | +20 extra |
| oi_confirmation | open_interest 存在且非 0 | +25 |
| volume_confirmation | volume 存在且非 0 | +20 |
| funding_extreme | abs(funding) >= 0.01 | +20 |
| multi_asset_sync | context 中同向资产 >= 3 | +25 |
| missing key field | OI/volume 缺失 | -10 each |

### 决策逻辑

| 决策 | 条件 |
|------|------|
| **allow** | price_move + >=1 确认因子 或 strong_price_move + multi_asset_sync |
| **observe** | price_move 但无确认因子，或字段不足但价格异常 |
| **block** | price_move 不命中，或字段严重不足 |

### 分层

| Tier | 分数范围 |
|------|---------|
| high | >= 70 |
| medium | 45–69 |
| low | < 45 |

---

## 7. v1.11-A 复盘问题对照

| v1.11-A 发现 | v1.11-B 如何解决 |
|-------------|-----------------|
| ARB 同资产 11min 重复发送 3 次 | value gate 不解决同资产冷却（需 pre_send_gate 层面），但 OI 极小的信号 score 更低 |
| 所有 funding 均为 ~0.00% | funding_extreme 因子仅在 funding >= 1% 时命中；near-zero funding 自动添加 warning |
| OI/Volume 只展示绝对值 | 当前字段限制，value gate 至少验证字段存在且非 0 |
| 跌幅播报无情报增量 | 必须有至少 1 个确认因子才能 allow |

---

## 8. 安全声明

| 检查项 | 状态 |
|--------|------|
| 是否真实发送 TG | 否 |
| 是否发正式频道 | 否 |
| 是否启动后台循环 | 否 |
| 是否使用付费 API | 否 |
| 是否读取/打印密钥 | 否 |
| 是否加载 secrets | 否 |
| 是否删除文件 | 否 |
| 是否新增数据源 | 否 |
| 是否 fake result | 否 |

---

## 9. 未完成项 / 风险

| 项目 | 说明 |
|------|------|
| 同资产冷却 | value gate 不负责冷却逻辑，需在 pre_send_gate 或 sender 层单独实现 |
| OI/Volume 相对变化 | 当前仅验证字段存在且非零，不判断"OI 24h delta%"或"volume surge ratio"。需新数据采集后才能增强 |
| 动态阈值 | 当前阈值为固定值（5%/8%），未按波动分位数动态调整。Phase 2 可引入 |
| dry-run only | 本轮未接入真实发送链路。value gate 结果独立输出 JSON，未影响现有 TG 发送流程 |
| context 构造 | dry-run 中 context 使用全部 fixture signals，生产环境应使用同时间窗口内的实际 signals |

---

## 10. 下一步建议

1. **优先**: 将 SignalValueGate 接入 `pre_send_gate` 链路，作为 gate check 的第三层（SignalTrustGate → SignalValueGate → Payload validation）
2. **其次**: 使用 10-20 条历史真实 signal 做 dry-run 复盘，验证 allow/observe/block 分布是否合理
3. **后续**: 在 OI/Volume 24h delta 数据可用后，增强 oi_confirmation 和 volume_confirmation 的判断逻辑

---

## 11. 给 Gemini 下一轮复核的回答

**Q: SignalValueGate 是否已经足够阻止"行情播报型噪音"？**

部分足够。value gate 要求至少 1 个确认因子才能 allow，这意味着纯价格波动的信号会被降级为 observe。但当前确认因子仅检查字段是否存在且非零，不判断"OI 变化是否异常"或"volume 是否放量"。在真实数据环境中，funding 长期为 0 的问题仍会导致 funding_extreme 几乎从来不命中。

**Q: allow / observe / block 三层是否适合后续接入测试频道发送链路？**

适合。allow 信号可以直接进入发送候选；observe 信号可以累积到一定数量后批量 review，或仅在无 allow 信号时作为候补；block 信号完全不进入发送流程。三层设计为后续的差异化发送策略提供了清晰的基础。

**Q: 下一步应该把 SignalValueGate 接入 pre_send_gate，还是先做 10-20 条历史样本 dry-run 复盘？**

建议先做历史样本 dry-run 复盘。因为接入 pre_send_gate 会直接影响发送行为，需要先用真实历史数据验证决策分布的合理性。如果复盘发现 allow 过多或过少，可以调整阈值后再接入。

---

⚠️ 仅供观察，不构成交易建议。
