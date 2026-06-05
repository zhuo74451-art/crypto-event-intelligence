# Market Radar v1.12-Z — Degraded Whale Envelope Compatibility Handoff

**Generated**: 2026-06-05 05:49:41 UTC+8
**Version**: v112Z
**Run ID**: 20260605_022952
**Task ID**: 20260605_v112z_degraded_whale_envelope_compatibility

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/run_market_radar_v112z_degraded_whale_envelope_compatibility.py` | 新增 | v112Z degraded whale envelope runner |
| `scripts/test_market_radar_v112z_degraded_whale_envelope_compatibility.py` | 新增 | v112Z test suite |
| `results/market_radar_v112z_degraded_whale_envelopes.jsonl` | 新增 | Degraded whale envelopes JSONL |
| `results/market_radar_v112z_degraded_whale_envelope_compatibility_result.json` | 新增 | Result JSON |
| `runs/market_radar/v112z_degraded_whale_envelope_compatibility.md` | 新增 | Markdown 报告 |
| `runs/market_radar/v112z_degraded_whale_envelope_compatibility_handoff.md` | 新增 | Handoff（本文件） |

---

## 执行命令

```powershell
cd C:\Users\PC\Desktop\Projects\事件情报系统
python scripts/run_market_radar_v112z_degraded_whale_envelope_compatibility.py
python scripts/test_market_radar_v112z_degraded_whale_envelope_compatibility.py
```

---

## 输入与输出

| 指标 | 值 |
|------|-----|
| Input records | 10 |
| Output envelopes | 10 |
| Unique addresses | 4 |
| All input degraded=true | True |
| All input mock_replay_only=true | True |
| All input eligible_for_real_send=false | True |

---

## Label Confidence 摘要

| 置信度 | 数量 |
|--------|------|
| high | 0 |
| medium | 8 |
| low | 2 |
| unknown | 0 |

⚠️ 无 high confidence 标签。medium 和 low 标签均正确保留，未伪装。

---

## Quality Flags 摘要

| Flag | 出现次数 |
|------|----------|
| degraded_label_confidence | 10 |
| delta_unavailable | 10 |
| liquidation_price_missing | 7 |
| local_timestamp_only | 10 |

---

## Routing Guard 摘要

| Guard | 值 |
|-------|-----|
| eligible_for_real_send | ALL FALSE |
| real_send_candidate | ALL FALSE |
| preview_allowed | ALL FALSE |
| tg_send_allowed | ALL FALSE |
| prod_state_write_allowed | ALL FALSE |

---

## Safety Invariant 状态

| Invariant | 状态 |
|-----------|------|
| No external API calls | ✅ |
| No credentials read | ✅ |
| No TG send | ✅ |
| No prod state write | ✅ |
| No daemon/watcher/cron/loop | ✅ |
| No files deleted | ✅ |
| Degraded envelopes NOT disguised as live passed | ✅ |
| Low-confidence labels NOT disguised as confirmed institutions | ✅ |
| All quality flags preserved | ✅ |
| All label confidence preserved | ✅ |
| All liquidation_price notes preserved | ✅ |
| All delta_status preserved | ✅ |
| All timestamp_status preserved | ✅ |

---

## 下一步建议

v113a: degraded whale preview pack local-only — 生成本地预览卡片，
但仍不进入 TG send path。
