# Market Radar v1.19B — Operator Decision Table (B-lite)

**Generated**: 2026-06-05T18:48:37+08:00
**Run ID**: 20260605_184831
**Task ID**: 20260605_v119b_signal_quality_b_lite_and_dashboard_guidance
**Pipeline**: v1.19B

---

## Decision Summary

**Total Cards**: 5

| Decision | Count |
|---|--------|
| accept | 1 |
| manual_required | 1 |
| reject | 1 |
| watch | 2 |

---

## Full Decision Table

| # | Card Family | Pipeline | Decision | B-lite Tier | Publishability | Evidence |
|---|------------|----------|----------|-------------|----------------|----------|
| 1 | `multi_asset_market_sync` | active | **✅ ACCEPT** | `N/A` | test_group_only | Live Binance public API: 3 assets fetched. Gate: Multi-asset data available for 3 assets.... |
| 2 | `price_oi_volume_anomaly` | blocked | **👀 WATCH** | `mild_watch` | blocked | Live Binance + OI: 3 signals. B-lite tier=mild_watch. Mild anomaly — observation only, NOT accept.... |
| 3 | `news_event_market_impact` | active | **👀 WATCH** | `N/A` | test_group_only_with_caveat | News: 51 events from 4 sources. Fresh=4, Stale=0. Entities: BINANCE, BTC. observation_only=true, not... |
| 4 | `liquidation_pressure` | blocked | **❌ REJECT** | `N/A` | blocked | Fixture: composite=0.35, threshold=0.60. Calm market. Threshold NOT lowered.... |
| 5 | `whale_position_alert` | blocked | **🔒 MANUAL** | `N/A` | blocked | Fixture: 4 addresses tracked (~$135M). Manual evidence NOT provided. Manual evidence NOT bypassed.... |

---

## Key Constraints Verified

- ✅ All 5 card families present
- ✅ whale_position_alert → `manual_required` (NOT bypassed)
- ✅ liquidation_pressure → `reject` (threshold NOT lowered)
- ✅ news_event_market_impact → `observation_only=true`, `not_causal_proof=true`
- ✅ price_oi_volume_anomaly → B-lite layered (reject/watch/accept)
- ✅ WATCH ≠ ACCEPT (mild anomalies are observation only)
- ✅ Live free public API data used for 3 card families
- ✅ No AI/model called
- ✅ No TG sent / No X/Twitter sent
- ✅ Production readiness: `false` / `0/5`
- ✅ No raw credentials in any output