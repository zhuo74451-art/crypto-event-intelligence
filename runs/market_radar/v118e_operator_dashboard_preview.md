# Market Radar v1.18E — Operator Dashboard Preview

**Generated**: 2026-06-05T18:21:34+08:00
**Run ID**: 20260605_182134
**Task ID**: 20260605_v118e_operator_dashboard_from_v118d_no_send_local_html
**Pipeline**: v1.18E
**Source Pipeline**: v1.18D

---

## Dashboard Summary

- **HTML Dashboard**: `runs/market_radar/v118e_operator_dashboard.html`
- **Mode**: local-only / no-send
- **Production Readiness**: false / 0/5

## Five-Card Status Overview

| Status | Count |
|---|--------|
| active | 2 |
| blocked | 2 |
| manual_required | 1 |

## Operator Decision Overview

| Decision | Count |
|---|--------|
| accept | 1 |
| watch | 1 |
| reject | 2 |
| manual_required | 1 |

## Operator Decision Table

| # | Card Family | v118C Status | Operator Decision | Publishability |
|---|------------|-------------|-------------------|----------------|
| 1 | `multi_asset_market_sync` | active | **✅ ACCEPT** | test_group_only |
| 2 | `price_oi_volume_anomaly` | blocked | **❌ REJECT** | blocked |
| 3 | `news_event_market_impact` | active | **👀 WATCH** | test_group_only_with_caveat |
| 4 | `liquidation_pressure` | blocked | **❌ REJECT** | blocked |
| 5 | `whale_position_alert` | manual_required | **🔒 MANUAL REQUIRED** | blocked |

## No-Send Confirmation

| Property | Value |
|---|--------|
| telegram_send | false |
| x_twitter_send | false |
| production_send | false |
| daemon_or_loop_started | false |
| external_api_called | false |
| ai_model_called | false |

## Production Readiness

**false / 0/5**

> NOT FOR LIVE USE. All 5 production readiness criteria remain unmet. The system operates on free public data sources only. News event extraction is rule-based, not causal. Liquidation gate requires high-volatility detection. Whale tracking requires manual address attribution. No automated decision-making is production-grade.

## Contract Validation

**All checks passed**: `True`

## Risk Warnings

- ⚠️ No production readiness (0/5)
- ⚠️ No X/Twitter send
- ⚠️ No production send
- ⚠️ No daemon/loop
- ⚠️ No external calls in v118E