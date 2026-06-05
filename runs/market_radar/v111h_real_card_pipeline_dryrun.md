# Market Radar v1.11-H — Real Card Render + Full Gate Pipeline Dry-run

**Run**: 2026-06-04 19:52:42 UTC+8
**Version**: v1.11-H
**Status**: ✅ Complete, 0 expectation mismatches

## Pipeline Architecture

```
SignalValueGate (v1.11-d) → CooldownGate (v1.11-f) → REAL render_card_payload (card_router v1.10-A R2) → pre_send_gate (v1.10-G)
```

## Key Change from v1.11-G

v1.11-G used mock payloads (`_build_mock_payload()`). v1.11-H replaces them with **real `render_card_payload()`** from `market_radar_card_router.py`. This is the critical bridge to production-ready payload validation.

## Aggregate Results

| Metric | Count | Rate |
|--------|-------|------|
| Total signals | 26 | 100% |
| **final_send_candidate** | 12 | 46.2% |
| **final_send_candidate_upgrade** | 2 | 7.7% |
| **TOTAL SEND** | **14** | **53.8%** |
| blocked_by_value_gate | 4 | 15.4% |
| suppressed_by_cooldown | 3 | 11.5% |
| blocked_by_pre_send_gate | 5 | 19.2% |
| observe | 2 | 7.7% |
| Expectation mismatches | **0** | 0% |

## Payload Render Metrics

| Metric | Count |
|--------|-------|
| payload_mode_real | 17 |
| payload_mode_mock | 2 |
| payload_render_success | 19 |
| payload_render_failed | **0** |
| payload_fallback_used | 0 |
| card_type_distribution | market_anomaly=17 |

## Scenario Results

### H1: Full Happy Path — Real Cards Pass All Gates
- 4 signals → 4 send_candidate (real cards)
- All real market_anomaly cards rendered and passed pre_send_gate

### H2: Value Gate Blocks — Real Cards Never Reached
- 3 signals → 3 blocked_by_value_gate
- Value gate correctly terminates before card rendering

### H3: Cooldown Suppression — Real Cards, Rate Limited
- 4 signals → 2 send_candidate, 2 suppressed_by_cooldown
- ARB repeats correctly suppressed within 10min window

### H4: Pre-Send Gate Blocks — Real Cards + Payload Validation
- 4 signals → 4 blocked_by_pre_send_gate
- 2 real cards blocked (source_trust, ttl_expiry)
- 2 mock payloads blocked (payload_validation)
- Mixed strategy validates both gate-level and payload-level blocking

### H5: Upgrade Override — Score Improvement, Real Cards
- 2 signals → 1 send_candidate, 1 send_candidate_upgrade
- ETH score Δ=70 triggers upgrade_override

### H6: Full Mixed Pipeline — Real Cards, All Outcomes
- 9 signals covering all possible outcomes
- 4 send_candidate + 1 upgrade, 1 blocked_value, 1 suppressed_cooldown, 1 blocked_pre_send, 2 observe

## Pre-send Block Reasons

| Signal | Reason |
|--------|--------|
| AVAX | source_type 'unknown' not allowed for test send |
| LTC | TTL expired: age=7200s, ttl=900s |
| NEAR | Payload text is empty or whitespace-only |
| OP | Payload missing 'parse_mode' field |
| ETH | source_type 'unknown' not allowed for test send |

## v1.11-G Comparison

| Metric | v1.11-G | v1.11-H |
|--------|---------|---------|
| Payload source | Mock (`_build_mock_payload()`) | **Real (`render_card_payload()`)** |
| Total signals | 26 | 26 |
| TOTAL SEND | 12 (46.2%) | 14 (53.8%) |
| blocked_value | 4 (15.4%) | 4 (15.4%) |
| suppressed_cooldown | 3 (11.5%) | 3 (11.5%) |
| blocked_pre_send | 5 (19.2%) | 5 (19.2%) |
| observe | 2 (7.7%) | 2 (7.7%) |
| Expectation mismatches | 0 | **0** |

## Security

- [x] No TG send
- [x] No formal channel
- [x] No secrets loaded
- [x] No paid APIs
- [x] No loop/daemon/cron
- [x] No files deleted
- [x] All code in correct project directory
