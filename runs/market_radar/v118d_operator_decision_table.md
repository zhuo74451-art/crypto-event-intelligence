# Market Radar v1.18D — Operator Decision Table

**Generated**: 2026-06-05T18:12:03+08:00
**Run ID**: 20260605_181203
**Source**: v118C five-card snapshot (read-only)

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

| # | Card Family | v118C Status | Operator Decision | Publishability | Evidence Summary | Reason | Next Operator Action |
|---|------------|-------------|-------------------|----------------|-----------------|--------|---------------------|
| 1 | `multi_asset_market_sync` | active | **ACCEPT** | test_group_only | v118C status=active, send_eligible=True. Signal: BTCUSDT: -0.44%; ETHUSDT: -4.52... | Multi-asset sync card is active with real Binance public API data. All monitored... | Review individual asset deltas. Confirm no stale ticker data. If correlation > 0... |
| 2 | `price_oi_volume_anomaly` | blocked | **REJECT** | blocked | v118C status=blocked. Gate: No asset passed admission threshold — insufficient a... | No asset passed the admission threshold — insufficient anomaly signal strength. ... | No action needed. Retry during higher-volatility windows. Do NOT lower threshold... |
| 3 | `news_event_market_impact` | active | **WATCH** | test_group_only_with_caveat | v118C status=active, observation_only=True, not_causal_proof=True. Signal: [high... | News event detected with measurable market context. However, event-market correl... | Read the full article at source URL before citing. Cross-reference with at least... |
| 4 | `liquidation_pressure` | blocked | **REJECT** | blocked | v118C status=blocked. Gate: Liquidation gate: blocked — calm market conditions (... | Liquidation gate is CORRECTLY blocked. Calm market conditions (composite_score=0... | No action needed. DO NOT lower threshold. Monitor for volatility regime change. ... |
| 5 | `whale_position_alert` | manual_required | **MANUAL** | blocked | v118C status=manual_required. 4 addresses tracked (total exposure ~$135M). Addre... | Whale position tracking requires manual on-chain address attribution evidence. N... | Complete v116N whale evidence workbook: 1) Verify each address label against at ... |

---

## Key Constraints Verified

- ✅ All 5 card families present in decision table
- ✅ whale_position_alert → `manual_required` (NOT bypassed)
- ✅ liquidation_pressure → `reject` (NOT accepted, threshold NOT lowered)
- ✅ news_event_market_impact → `observation_only=true`, `not_causal_proof=true`
- ✅ All decisions from allowed set: {accept, watch, reject, manual_required}
- ✅ No external API calls (Binance, RSS, Telegram, AI/model)
- ✅ Production readiness: `false` / `0/5`
- ✅ No raw credentials in any output
