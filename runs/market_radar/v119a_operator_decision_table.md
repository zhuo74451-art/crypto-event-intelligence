# Market Radar v1.19A — Operator Decision Table

**Generated**: 2026-06-05T18:31:38+08:00
**Run ID**: 20260605_183130
**Task ID**: 20260605_v119a_live_no_send_operator_one_shot_refresh_flow
**Pipeline**: v1.19A

---

## Decision Summary

**Total Cards**: 5

| Decision | Count |
|---|--------|
| accept | 1 |
| manual_required | 1 |
| reject | 2 |
| watch | 1 |

---

## Full Decision Table

| # | Card Family | Pipeline Status | Operator Decision | Publishability | Evidence Summary | Next Operator Action |
|---|------------|-----------------|-------------------|----------------|-----------------|---------------------|
| 1 | `multi_asset_market_sync` | active | **✅ ACCEPT** | test_group_only | Live Binance public API: 3 assets fetched. Gate: Multi-asset data available for 3 assets. Source: fr... | Review individual asset deltas. Confirm no stale ticker data. If correlation > 0.7 persists, card is... |
| 2 | `price_oi_volume_anomaly` | blocked | **❌ REJECT** | blocked | Gate blocked: No asset passed admission threshold — insufficient anomaly signal strength. All signal... | No action needed. Retry during higher-volatility windows. Do NOT lower threshold to force card gener... |
| 3 | `news_event_market_impact` | active | **👀 WATCH** | test_group_only_with_caveat | Live RSS/news: 4 sources, 50 events extracted. Extraction method: rule_based_keyword_matching. obser... | Read the full article at source URL before citing. Cross-reference with at least one other news sour... |
| 4 | `liquidation_pressure` | blocked | **❌ REJECT** | blocked | Fixture: composite=0.35, threshold=0.60. Calm market. Threshold NOT lowered. Gate: Liquidation gate:... | No action needed. DO NOT lower threshold. Monitor for volatility regime change. When composite_score... |
| 5 | `whale_position_alert` | blocked | **🔒 MANUAL** | blocked | Fixture: 4 addresses tracked (total exposure ~$135M). Manual evidence: NOT PROVIDED (False). Manual ... | Complete v116N whale evidence workbook: 1) Verify each address label against at least 2 on-chain sou... |

---

## Key Constraints Verified

- ✅ All 5 card families present in decision table
- ✅ whale_position_alert → `manual_required` (NOT bypassed)
- ✅ liquidation_pressure → `reject` (NOT accepted, threshold NOT lowered)
- ✅ news_event_market_impact → `observation_only=true`, `not_causal_proof=true`
- ✅ All decisions from allowed set: {accept, watch, reject, manual_required}
- ✅ Live free public API data used for 3 card families
- ✅ No AI/model called
- ✅ No TG sent
- ✅ No X/Twitter sent
- ✅ No production writes
- ✅ No daemon/cron/loop started
- ✅ Production readiness: `false` / `0/5`
- ✅ No raw credentials in any output