# Market Radar v1.18B — Five-Card Operator Snapshot with Blocked Gate Overlay Report

**Generated**: 2026-06-05T17:34:28+08:00
**Run ID**: 20260605_173357
**Task ID**: 20260605_v118b_five_card_operator_snapshot_with_blocked_gate_overlay

---

## Purpose

v118B upgrades from v118A three-card digest to a **five-card operator snapshot**:

1. **3 real free-data adapter cards** run through the shared pipeline (same as v118A)
2. **2 blocked overlay cards** (liquidation_pressure + whale_position_alert) generated using existing gate/checklist/v116N blocking rationale
3. **One unified five-card operator snapshot** with clear status labels
4. **At most 1 TG message** is sent (aggregated snapshot)

---

## Five-Card Pipeline Results

| Card Family | Status | Data Source | Send Eligible | Fetch Count |
|------------|--------|-------------|---------------|-------------|
| `news_event_market_impact` | active | free_public_source | Yes | 1 |
| `price_oi_volume_anomaly` | blocked | free_public_api | No | 1 |
| `multi_asset_market_sync` | active | free_public_api | Yes | 1 |
| `liquidation_pressure` | blocked | fixture_blocked_overlay | No | 0 |
| `whale_position_alert` | manual_requi | fixture_blocked_overlay | No | 0 |


## Card Family Status Breakdown

### Active (via shared pipeline)
- **2 card(s)** active through quality gate

### Blocked / Waiting for Conditions
- **2 card(s)** blocked by gate or conditions

### Manual Evidence Required
- **1 card(s)** require manual evidence

---

## TG Test Group Send

❌ **FAILED** — Network or transport error.

- Reason: `TG send failed: [http_status_error] (transport_error_type=PROVIDER_REJECTION) Bad Request: can't parse entities: Unsupported start tag "" at byte offset 1046 (host=api.telegram.org, timeout=10s, proxy_detected=False)`

---

## Operator Snapshot Summary

- **Cards in snapshot**: 5 (5 target)
- **Real adapter cards**: 3
- **Blocked overlay cards**: 2
- **Active**: 2
- **Blocked**: 2
- **Manual required**: 1
- **Snapshot length**: 1384 chars (TG-safe)

## Liquidation Gate Verification

- ✅ Gate NOT lowered (threshold=0.60 maintained)
- ✅ No fake liquidation spike created
- ✅ Calm market correctly results in blocked status
- ✅ v116N gate rationale applied

## Whale Gate Verification

- ✅ Manual evidence NOT bypassed
- ✅ No auto-guessed address attribution
- ✅ v116N manual evidence checklist applied
- ✅ Correctly set to manual_required status

## Data Sources (All Free Public)

| Source | Type | Auth Required |
|--------|------|---------------|
| Binance /api/v3/ticker/24hr | Free public REST | None |
| Binance /fapi/v1/openInterest | Free public REST | None |
| CoinDesk/Cointelegraph/Decrypt/The Block | Free public RSS | None |
| Binance announcements | Free public API | None |
| Fixture overlay (liquidation) | Local fixture | N/A |
| Fixture overlay (whale) | Local fixture | N/A |

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | ✅ |
| TG messages sent this run | 0 (max 1) |
| Production send | ❌ NEVER |
| X/Twitter send | ❌ NEVER |
| Credentials printed | ❌ NEVER |
| Daemon/loop started | ❌ NEVER |
| Files deleted | ❌ NEVER |
| v116 history modified | ❌ NEVER |
| AI model called | ❌ NEVER |
| Evidence ledger clean | ✅ |
| Each adapter ≤1 fetch | ✅ |
| All 5 card families in snapshot | ✅ |

## Secret Leak Risk Assessment

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Snapshot preview: no raw secrets
- ✅ Operator snapshot contains no raw credentials

## News Event Guard

- ✅ observation_only = True
- ✅ not_causal_proof = True
- ✅ No deterministic causal language in snapshot
- ✅ All event extraction is rule-based (NO AI/model)

## Production Readiness

**0/5 — NOT FOR LIVE USE**

All minimum conditions remain unmet. Production send is NEVER enabled.

## Five-Card Evolution

- v117C → multi_asset_market_sync (card 1)
- v117D → price_oi_volume_anomaly (card 2)
- v117F → news_event_market_impact (card 3)
- v118A → three-card digest (cards 1-3 unified)
- **v118B → five-card operator snapshot (cards 1-3 real + cards 4-5 blocked overlay)**

## Test Results Summary

(To be filled after running tests)

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v118B tests | Pass | (run) |
| v118A regression | Pass | (run) |
| v117F regression | Pass | (run) |
| v117E regression | Pass | (run) |
| v117D regression | Pass | (run) |
| v117C regression | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |
