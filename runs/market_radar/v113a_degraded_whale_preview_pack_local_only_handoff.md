# Market Radar v1.13-A — Degraded Whale Preview Pack (Local Only) Handoff

**Generated**: 2026-06-05 05:56:54 UTC+8
**Version**: v113A
**Run ID**: 20260605_022952
**Task ID**: 20260605_v113a_degraded_whale_preview_pack_local_only

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/run_market_radar_v113a_degraded_whale_preview_pack_local_only.py` | 新增 | v113A degraded whale preview pack runner |
| `scripts/test_market_radar_v113a_degraded_whale_preview_pack_local_only.py` | 新增 | v113A test suite |
| `results/market_radar_v113a_degraded_whale_preview_cards.jsonl` | 新增 | Preview cards JSONL |
| `results/market_radar_v113a_degraded_whale_preview_pack_result.json` | 新增 | Result JSON |
| `runs/market_radar/v113a_degraded_whale_preview_pack_local_only.md` | 新增 | Markdown 报告 |
| `runs/market_radar/v113a_degraded_whale_preview_pack_local_only_handoff.md` | 新增 | Handoff（本文件） |

---

## 执行命令

```powershell
cd C:\Users\PC\Desktop\Projects\事件情报系统
python scripts/run_market_radar_v113a_degraded_whale_preview_pack_local_only.py
python scripts/test_market_radar_v113a_degraded_whale_preview_pack_local_only.py
```

---

## 输入与输出

| 指标 | 值 |
|------|-----|
| Input envelopes | 10 |
| Output preview cards | 10 |
| Cards == envelopes | True |
| All preconditions met | True |
| All cards valid | True |
| Build errors | 0 |

---

## Label Confidence 摘要

| 置信度 | 数量 |
|--------|------|
| high | 0 |
| medium | 8 |
| low | 2 |
| unknown | 0 |

⚠️ 无 high confidence 标签。所有 medium/low 标签均正确保留 label_explanation，
未伪装成确定机构。

---

## Warning 摘要

| Warning | 出现次数 |
|---------|----------|
| 使用本地观察时间，非 HyperLiquid 服务端时间 | 10 |
| 单次快照，暂无法计算仓位变化 | 10 |
| 标签置信度不足 | 10 |
| 清算价格不可用 | 7 |

---

## Routing Guard 摘要

| Guard | 值 |
|-------|-----|
| local_preview_only | ALL TRUE |
| eligible_for_real_send | ALL FALSE |
| real_send_candidate | ALL FALSE |
| tg_send_allowed | ALL FALSE |
| prod_state_write_allowed | ALL FALSE |

---

## Safety Invariant 状态

| Invariant | 状态 |
|-----------|------|
| No external API calls | ✅ |
| No AI/API/model calls | ✅ |
| No credentials read | ✅ |
| No TG send | ✅ |
| No prod state write | ✅ |
| No daemon/watcher/cron/loop | ✅ |
| No files deleted | ✅ |
| Degraded preview NOT disguised as live passed | ✅ |
| Low-confidence labels NOT disguised as confirmed institutions | ✅ |
| All label_confidence preserved | ✅ |
| All null liquidation_price show '清算价格不可用' | ✅ |
| All delta unavailable show explanation | ✅ |
| All local timestamp show '本地观察时间' | ✅ |

---

## 下一步建议

v113b: degraded whale preview quality gate local-only — 
对 preview card 质量建立关卡验证，确保展示层完整覆盖降级场景。
