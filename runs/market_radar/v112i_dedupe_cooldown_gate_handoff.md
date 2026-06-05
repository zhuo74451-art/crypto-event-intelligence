# Market Radar v1.12-I — Dedupe + Cooldown Gate Handoff

**Generated**: 2026-06-05 04:13:19 UTC+8
**Version**: v1.12-I
**Run ID**: 20260604_202718
**Task ID**: 20260604_202718.r18

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/market_radar_dedupe_cooldown_gate_v112i.py` | 新增 | Dedupe + Cooldown Gate 核心模块 |
| `scripts/run_market_radar_v112i_dedupe_cooldown_gate.py` | 新增 | v112i Gate runner |
| `scripts/test_market_radar_dedupe_cooldown_gate_v112i.py` | 新增 | v112i Gate 测试套件 |
| `data/fixtures/market_radar_v112i_prior_signal_state.json` | 新增 | Prior state fixture (7 entries) |
| `results/market_radar_v112i_dedupe_cooldown_gate_result.json` | 新增 | 结果 JSON |
| `results/market_radar_v112i_gate_decisions.jsonl` | 新增 | Gate decisions JSONL |
| `runs/market_radar/v112i_dedupe_cooldown_gate.md` | 新增 | Markdown 报告 |
| `runs/market_radar/v112i_dedupe_cooldown_gate_handoff.md` | 新增 | Handoff（本文件） |

---

## 执行命令

```powershell
cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统
python scripts/run_market_radar_v112h_unified_signal_envelope.py
python scripts/run_market_radar_v112i_dedupe_cooldown_gate.py
python scripts/test_market_radar_dedupe_cooldown_gate_v112i.py
```

---

## Gate 统计

| 指标 | 值 |
|------|-----|
| input_envelope_count | 13 |
| decision_count | 13 |
| passed_count | 9 |
| blocked_dedupe_count | 2 |
| blocked_cooldown_count | 2 |
| eligible_for_send_count | 9 |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| decision_count_matches_input | True |

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

## Pipeline 确认

Pipeline 已建立：

```
adapter output -> signal envelope -> dedupe/cooldown gate -> eligible signals
```

| 阶段 | 状态 |
|------|------|
| v112h envelope 生成 | Done |
| v112i dedupe/cooldown gate | Done |
| TG send | Not connected |
| Live data | Not connected |

---

## 下一步建议

1. Dedupe + Cooldown Gate 层已建立并通过测试。
2. 所有 envelope 都生成了 gate decision。
3. Dedupe matching 工作正常 — 同 dedupe_key 的重复信号被正确 block。
4. Cooldown matching 工作正常 — 同 cooldown_key 且在冷却期内的信号被正确 block。
5. 不同 card_type 不互相干扰，同资产不同方向不错误 block。
6. 下一步可以接入真实数据源，或将 eligible signals 送入 sender。
