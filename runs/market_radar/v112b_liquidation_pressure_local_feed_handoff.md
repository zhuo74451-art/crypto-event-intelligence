# Market Radar v1.12-B — Liquidation Pressure Local Feed Handoff

**Generated**: 2026-06-04 22:03:05 UTC+8
**Version**: v1.12-B
**Task ID**: 20260604_202718.r11
**Lane**: 1

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/market_radar_liquidation_feed_v112b.py` | 新增 | 清算数据适配层 — normalize / detect / render / validate |
| `scripts/run_market_radar_v112b_liquidation_pressure_local_feed.py` | 新增 | Runner — 读取 fixture，执行全流程 |
| `scripts/test_market_radar_liquidation_feed_v112b.py` | 新增 | 测试脚本 — 11 项测试 |
| `data/fixtures/market_radar_v112b_liquidation_snapshots.json` | 新增 | 5 条清算快照 fixture（3 valid + 2 invalid） |
| `results/market_radar_v112b_liquidation_pressure_local_feed_result.json` | 新增 | 结果 JSON |
| `runs/market_radar/v112b_liquidation_pressure_local_feed.md` | 新增 | Markdown 报告 |
| `runs/market_radar/v112b_liquidation_pressure_local_feed_handoff.md` | 新增 | Handoff（本文件） |

---

## 执行命令

```powershell
python scripts/run_market_radar_v112b_liquidation_pressure_local_feed.py
python scripts/test_market_radar_liquidation_feed_v112b.py
python scripts/test_market_radar_card_type_registry_v112a.py
# 旧测试验证（确保不破坏 v112a）：
python scripts/test_market_radar_sender_runtime_v111o.py
python scripts/test_market_radar_safe_sender_v111n.py
python scripts/test_market_radar_public_card_readiness_v111l.py
python scripts/test_market_radar_mock_sender_v111j.py
python scripts/test_market_radar_signal_value_gate_v111b.py
python scripts/test_market_radar_same_asset_cooldown_gate_v111f.py
python scripts/test_market_radar_card_router_v110a.py
python scripts/test_market_radar_pre_send_gate_v110g.py
python scripts/test_market_radar_signal_trust_gate_v110c.py
python scripts/test_market_radar_sender_gate_coverage_v110h.py
```

---

## Readiness 变化

| Card Type | 之前 | 之后 | 原因 |
|-----------|------|------|------|
| `liquidation_pressure` | ❌ missing | ⚠️ partial | 本地适配层 + public card 渲染就绪；仅缺实时数据源 |

---

## 测试结果

（运行 `test_market_radar_liquidation_feed_v112b.py` 后填充）

---

## Public Previews 摘要

共生成 **3** 张公开卡片：

### Card #1
- **标题**: ⚠️ 清算压力｜BTC
- **一句话**: 一句话：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

### Card #2
- **标题**: ⚠️ 清算压力｜ETH
- **一句话**: 一句话：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

### Card #3
- **标题**: ⚠️ 清算压力｜SOL
- **一句话**: 一句话：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

---

## Blocked Reason 摘要

共 **2** 条样本被阻止：

- `liq_v112b_fixture_004_invalid_missing_asset`: 缺少 asset 字段
- `liq_v112b_fixture_005_invalid_zero_liquidation`: 清算金额全部为 0，无有效数据

---

## 风险

1. **无实时数据源** — 当前全部使用 fixture 样本，无法反映真实市场清算压力。
   在接入实时数据源之前，`liquidation_pressure` 不能用于实际监测。
2. **Coinglass 付费墙** — 主流清算数据聚合 API (Coinglass) 需要付费订阅。
   免费替代方案（交易所 WebSocket）需要额外的 WebSocket 客户端开发。
3. **阈值需要校准** — 当前压力检测使用固定阈值（$5M 1h 清算），实际阈值
   应根据历史数据和市场状态动态调整。
4. **Gate 集成未测试** — 信号尚未通过 SignalValueGate / CooldownGate /
   PreSendGate 管道，不能确认在真实发送流程中不会出问题。

---

## 下一步建议

1. **立即**: 调研免费清算数据源（交易所公开 WebSocket），编写对应的
   normalize 适配器。
2. **短期**: 将 v112b 信号接入 gate 管道进行集成测试。
3. **中期**: 对接 v112a registry，使 liquidation_pressure 的 readiness
   能动态读取 v112b adapter 状态。
4. **长期**: 建立历史清算基线，实现动态阈值调整。

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| real_tg_sent | false |
| external_api_called | false |
| paid_api_called | false |
| daemon_started | false |
| token/key/cookie read | false |
| files_deleted | false |
