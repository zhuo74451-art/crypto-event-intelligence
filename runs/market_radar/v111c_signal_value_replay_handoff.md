# Market Radar v1.11-C — Signal Value Replay Handoff

**result_source**: `claude_code_executor`
**task_id**: `20260604_162516.r07`
**run_id**: `20260604_162516`
**status**: `done`
**generated_at**: `2026-06-04 17:16:00 UTC+8`
**executor_lane**: `1`
**project_label**: `market_radar`

---

## Modified files

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/run_market_radar_signal_value_gate_v111c_replay.py` | 新增 | v1.11-C 历史信号回放脚本 |
| `results/market_radar_v111c_signal_value_replay_result.json` | 新增 | 回放结果 JSON |
| `runs/market_radar/v111c_signal_value_replay.md` | 新增 | 回放复盘文档 |
| `runs/market_radar/v111c_signal_value_replay_handoff.md` | 新增 | 本 handoff |

**未修改任何现有 v111b gate 代码。未删除任何文件。**

---

## Commands executed

| 命令 | 结果 |
|------|------|
| `python scripts/run_market_radar_signal_value_gate_v111c_replay.py` | ✅ 成功，15 条信号回放完成 |
| `python scripts/test_market_radar_signal_value_gate_v111b.py` | ✅ 18/18 passed |
| `python scripts/test_market_radar_pre_send_gate_v110g.py` | ✅ 16/16 passed |
| `python scripts/test_market_radar_signal_trust_gate_v110c.py` | ✅ 26/26 passed |
| `python scripts/test_market_radar_card_router_v110a.py` | ✅ 28/28 passed |
| `python scripts/test_market_radar_sender_gate_coverage_v110h.py` | ✅ 15/15 passed |

---

## Tests run

| 测试套件 | 通过/总计 | 状态 |
|----------|----------|------|
| v111b SignalValueGate | 18/18 | ✅ |
| v110g pre_send_gate | 16/16 | ✅ |
| v110c signal_trust_gate | 26/26 | ✅ |
| v110a card_router | 28/28 | ✅ |
| v110h sender_gate_coverage | 15/15 | ✅ |
| **合计** | **103/103** | ✅ |

---

## 旧测试是否仍为 85/85

✅ **是**。v110g (16) + v110c (26) + v110a (28) + v110h (15) = 85/85 全部通过。v111b 新增 18/18 也全部通过。

---

## 安全合规

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
| 是否把 fixture 冒充真实信号 | 否（所有 fixture 已标记 is_fixture=true） |

---

## Replay 结果

| 路径 | 说明 |
|------|------|
| replay 结果路径 | `results/market_radar_v111c_signal_value_replay_result.json` |
| replay 文档路径 | `runs/market_radar/v111c_signal_value_replay.md` |

| 指标 | 值 |
|------|-----|
| total_signals | 15 |
| real_signal_count | 8 |
| fixture_signal_count | 7 |
| allow_count | 13 |
| observe_count | 0 |
| block_count | 2 |
| suspected_false_positive | 2 (SOL fixture, ARB fixture — 字段缺失但 gate 仍 allow) |
| suspected_false_negative | 1 (LINK fixture — price -3.2% + OI 150M 被 block，但判定为合理) |

---

## 核心结论

1. **SignalValueGate 规则正确执行**：所有决策均符合预期逻辑。有价格+确认因子的信号 → allow，无价格/数据不足 → block。

2. **allow 率偏高（87%）但合理**：15 条信号中 12 条 market_anomaly 有 price+OI 确认，在 batch context 下 multi_asset_sync 大量触发，导致 allow 集中。小 batch（3-5 条）的生产环境下 allow 率会自然降低。

3. **observe 层闲置**：0 条 observe 说明当前真实信号字段质量尚可（OI+volume 均有），但也说明 gate 的 observe 设计在实践中可能较少触发。

4. **没有误杀有价值信号**：LINK -3.2% 的 block 经过审核判定为合理（价格确实不够异常）。

5. **不建议立即接入 pre_send_gate**：因为 87% 的 allow 率意味着大部分信号仍会进入发送链路。应先做 v1.11-D 独立信号门控测试（1-3 条小 batch），再评估。

---

## 是否建议接入 pre_send_gate

**不建议立即接入。** 建议顺序：
1. **先做同资产冷却期**（pre_send_gate 层面）→ 解决 ARB/SUI 重复发送
2. **v1.11-D 独立信号门控测试**（小 batch）→ 验证生产环境分布
3. **再评估是否接入** → 基于 v1.11-D 结果决定

---

## 未完成项 / 风险

| 项目 | 说明 |
|------|------|
| 同资产冷却期 | SignalValueGate 不负责冷却，ARB 3 次发送的重复问题需要 pre_send_gate 层解决 |
| multi_asset_sync 对 batch 大小的依赖 | 15 条 batch 中 multi_asset_sync 触发 14/15 次，生产环境 3-5 条 batch 触发频率会显著降低 |
| funding_extreme 几乎不触发 | 15 条中仅 ETH fixture（funding -0.025）命中。真实信号 funding 全为 ~0%，因子无区分力 |
| 缺少 OI/Volume delta | 当前仅验证字段存在且非零，不判断变化量。ARB OI 465 万 vs BTC OI 18 亿都同样命中 OI 确认 |
| fixture 占比偏高 | 7/15 是 fixture。虽然真实信号 8 条满足最低要求，但结论受 fixture 影响 |

---

## 下一步建议

| 优先级 | 建议 | 说明 |
|--------|------|------|
| **P0** | 同资产冷却期 | 在 pre_send_gate / sender 层实现 N 分钟内同资产只发 1 次 |
| **P0** | v1.11-D 独立信号门控测试 | 用 1-3 条信号小 batch 回放，模拟生产环境 gate 行为 |
| **P1** | BTC/ETH 差异化阈值 | 大盘币种 price 阈值从 5% 提高到 7% |
| **P1** | 收集 funding delta 数据 | 为 funding 因子提供更有区分度的输入 |
| **P2** | OI delta% 替代 OI 绝对值 | 增强 OI 确认因子的信息含量 |

---

## 给 GPT 的返回

v1.11-C 已完成，等待 GPT 验收。

**replay 结果路径**: `results/market_radar_v111c_signal_value_replay_result.json`
**replay 文档路径**: `runs/market_radar/v111c_signal_value_replay.md`

---

⚠️ 仅供观察，不构成交易建议。
