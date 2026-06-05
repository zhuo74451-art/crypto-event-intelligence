# Market Radar v1.12-E — All Fixed Card Local Dry-Run Pipeline Handoff

**Generated**: 2026-06-05 04:13:18 UTC+8
**Version**: v1.12-E
**Run ID**: 20260604_202718
**Task ID**: 20260604_202718.r14

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py` | 新增 | 统一 5 类固定卡片 dry-run pipeline runner |
| `scripts/test_market_radar_all_fixed_card_pipeline_v112e.py` | 新增 | v112e 统一 pipeline 测试 |
| `results/market_radar_v112e_all_fixed_card_local_pipeline_result.json` | 新增 | 统一 pipeline 结果 JSON |
| `runs/market_radar/v112e_all_fixed_card_local_pipeline.md` | 新增 | Markdown 报告 |
| `runs/market_radar/v112e_all_fixed_card_local_pipeline_handoff.md` | 新增 | Handoff（本文件） |

---

## 执行命令

```powershell
cd C:\Users\PC\Desktop\Projects\事件情报系统
python scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py
python scripts/test_market_radar_all_fixed_card_pipeline_v112e.py
```

---

## 5 类固定卡片 Readiness Matrix

| # | Card Type | Readiness | Public Preview | Gate Tested | Live Ready |
|---|-----------|-----------|---------------|-------------|------------|
| 1 | `price_oi_volume_anomaly` | ✅ ready | ⚠️ fallback | ✅ | ❌ |
| 2 | `whale_position_alert` | ⚠️ partial | ✅ | ✅ | ❌ |
| 3 | `liquidation_pressure` | ⚠️ partial | ✅ | ✅ | ❌ |
| 4 | `multi_asset_market_sync` | ⚠️ partial | ✅ | ✅ | ❌ |
| 5 | `news_event_market_impact` | ⚠️ partial | ✅ | ✅ | ❌ |

**Final Matrix**: Ready=1, Partial=4, Missing=0

---

## 每类 Card Type Output Summary

### 多因子价格异动卡 (`price_oi_volume_anomaly`)

price_oi_volume_anomaly — READY: 0 public preview(s), schema complete, gate tested, fixture samples available. Monitoring gaps: OI/Volume delta real-time tracking, funding rate historical baseline, cross-exchange data consistency check.

### 巨鲸仓位警报卡 (`whale_position_alert`)

whale_position_alert — PARTIAL (v112f enrichment active): 6 real public preview(s) from v112f local enrichment, 6 valid signals. fallback_preview=false. Address labels + historical position sequence available (local fixture). Missing: live data source, multi-address aggregation, real-time liquidation alerts.

### 清算压力预警卡 (`liquidation_pressure`)

liquidation_pressure — PARTIAL: 3 public preview(s) from 5 fixture snapshots, 3 valid signals. live_ready=false. Missing: real-time liquidation data source, liquidation heatmap, historical liquidation baseline.

### 多资产共振卡 (`multi_asset_market_sync`)

multi_asset_market_sync — PARTIAL (v112g local correlation active): 5 real public preview(s) from v112g local correlation feed, 5 valid signals, 3 blocked. fallback_preview=false. Synchronized move score + direction agreement + sector/basket detection available (local fixture). Missing: live data source, real-time correlation matrix.

### 新闻事件影响卡 (`news_event_market_impact`)

news_event_market_impact — PARTIAL: 5 public preview(s) from 7 fixture events, 5 valid signals. live_ready=false. Missing: live news RSS/API pipeline, auto event classification (NLP), auto affected-assets extraction, pricing model.

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
| token/key/cookie read | false |
| files_deleted | false |

---

## Unfinished Items / Risks

- liquidation_pressure: 缺少实时清算数据源（当前仅 fixture）
- news_event_market_impact: 缺少实时新闻 RSS/API 接入管道（当前仅 fixture）
- whale_position_alert: 缺少地址标签自动标注和历史仓位序列追踪
- multi_asset_market_sync: 缺少跨资产实时相关性矩阵自动检测
- price_oi_volume_anomaly: OI/Volume delta 实时追踪待增强

---

## 下一步建议

1. **不需要马上接 live 数据源** — v1.12-E 已证明 5 类卡片统一 entry 可行，
   下一步应专注于提升「质量」而非「实时性」。
2. **优先补齐 Partial 卡片的核心 missing capability**：
   - liquidation_pressure: 接入免费清算数据聚合（如交易所 WebSocket）
   - news_event_market_impact: 接入免费新闻 RSS/API
   - whale_position_alert: 地址标签自动标注
   - multi_asset_market_sync: 跨资产相关性矩阵
3. **price_oi_volume_anomaly** 已 ready，可在其他卡片推进时并行增强。
