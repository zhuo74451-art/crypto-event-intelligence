# Signal Spine v1 — Release Candidate Independent Review

**Reviewer:** 独立 Release Candidate 验收负责人  
**Review Date:** 2026-06-16  
**Target Branch:** `workbench/overnight-signal-spine-v1`  
**Integration Commit:** `f7bf811d6e2cd6eba7dd4e938167e036915d5a44`  
**Price Backfill Commit (IO):** `7934b27e14fd2c3211cb9ed13c7d508b53dbcd9b`  
**Price Backfill RC Commit (IO):** `17aac4bfix(price-backfill): data integrity RC` (not in integration branch)

---

## Test Results Summary

| Test Suite | Branch | Passed | Failed | Notes |
|-----------|--------|--------|--------|-------|
| Core Spine tests | integration (f7bf811) | 64 | 0 | standard pipeline gate/registry/orchestrator |
| Integration cross-module tests | integration (f7bf811) | 32 | 0 | cross-source merge, dedup, atomicity, pump→BLOCK |
| IO lane tests | integration (f7bf811) | 30 | 0 | adapter, semantics, dry-run, golden, offline |
| **Total integration** | **f7bf811** | **126** | **0** | **all pass** |
| Subtest passes | integration (f7bf811) | 50 | 0 | fixture golden/offline subtests |
| Price backfill tests | IO (17aac4b) | 57 | 0 | mode system, max lag, decimal/percent, clock |
| IO lane tests | IO (989e3e1) | 31 | 0 | 50 subtests |
| **Total IO branch** | **IO** | **88** | **0** | **all pass** |

---

## 1. Release Blockers (Cannot Ship)

### RCB-1: Integration Demo Script Has Stale Import

**Severity:** RELEASE BLOCKER  
**File:** `scripts/run_signal_spine_v1_demo.py`  
**Line:** 63  
**Field/Function:** `from market_radar.shared.event_intelligence_semantics import DataQuality`

**Details:**  
The integration branch (`f7bf811`) renamed `DataQuality` to `DataOrigin` in `event_intelligence_semantics.py` to resolve P0-1 from the pre-integration review. However, the demo script at line 63 still imports `DataQuality` from `event_intelligence_semantics`. This causes an `ImportError` on every run.

**Reproduction:**
```bash
cd /path/to/integration/branch
python scripts/run_signal_spine_v1_demo.py --fixture --dry-run
# → ImportError: cannot import name 'DataQuality' from 'event_intelligence_semantics'
```

**Actual impact:** All downstream users (QA, demo reviewers, new contributors) cannot run the integration demo. The entire "Section A — F" verification pipeline is dead on the integration branch.

**Suggested fix:** Replace `from market_radar.shared.event_intelligence_semantics import DataQuality` with `from market_radar.shared.models import DataOrigin` and update all `data_quality=...` references to `data_origin=...` in the demo script.

### RCB-2: Price Backfill Module Missing from Integration Branch

**Severity:** RELEASE BLOCKER  
**File:** `market_radar/shared/event_price_backfill.py`  
**Info:** File does not exist in integration branch tree

**Details:**  
The integration branch (`f7bf811`) does NOT include `market_radar/shared/event_price_backfill.py`. This module exists only on the IO branch (commits `7934b27` and `17aac4b`). The integration manifest marks it as an IO lane deliverable that should be committed before Phase 2 integration, but it was never included.

**Actual impact:**
- Price backfill integration tests cannot run on the integration branch
- The EventIntelligenceMapper cannot call price data for risk assessment
- The "network with cache" mode and max lag protection (120s) in the IO RC are not available

**Suggested fix:** Merge `17aac4b` (or at minimum `7934b27`) from IO branch into the integration branch. Note that `17aac4b` has breaking changes to the `WindowReturn` dataclass (renamed `return_pct` to `return_decimal` + `return_percent`). The integration branch must update consumers accordingly.

---

## 2. Must Fix Before Price Integration

### PFI-1: Network Failure → Fixture Fallback in Integration Branch Price Backfill

**Severity:** MUST FIX  
**File:** `market_radar/shared/event_price_backfill.py` (not yet in integration branch)

**Integration branch behavior (would have this issue):**  
The `event_price_backfill.py` as seen in commit `7934b27` has `_fetch_klines()` that does:
```python
if self.use_fixture:
    return get_fixture_klines(symbol)
klines = fetch_klines(...)
if klines is not None:
    self._source = "binance_public_api"
    return klines
# Fallback to fixture
self._source = "fixture_fallback"
return get_fixture_klines(symbol)
```

This means ANY network failure silently falls back to fixture data and marks it `fixture_fallback`. A real event that fails to fetch live klines would receive fixture prices — creating a false sense of accuracy.

**IO RC fix (commit `17aac4b`):**  
The IO branch already fixed this with three explicit modes:
- `FIXTURE`: uses pre-built data, clearly marked
- `NETWORK`: failure → `unavailable`/`failed`, NEVER fixture
- `NETWORK_WITH_CACHE`: failure → disk cache, NEVER manual fixture

**Suggested fix:** When merging price backfill, use the IO RC version (`17aac4b`) which has the mode system. Do NOT use the `7934b27` version.

### PFI-2: 24h Kline Binance Limit=1000 Unaddressed

**Severity:** MUST FIX  
**File:** `market_radar/shared/event_price_backfill.py`  
**Function:** `fetch_klines()` / `fetch_klines_window()`

**Integration branch approach (`7934b27`):**  
Fetches all klines in one call with `limit=1500`:
```python
klines = fetch_klines(
    symbol=symbol, interval="1m", limit=1500,
    start_time=start_ms, end_time=end_ms,
)
```
Binance REST API has a max limit of 1000 per request for 1m klines. The `limit=1500` will be silently truncated to 1000, meaning only ~16.7h of data instead of the required 24h+1m. The missing klines for the 24h window would cause `select_window_kline()` to return `None`, marking the 24h window as `unavailable` even when the event is mature.

**IO RC fix (commit `17aac4b`):**  
Uses individual window requests via `fetch_klines_window()` with small `window_minutes + 2` limits. Each request covers only a narrow window around the target time, so limits are always well under 1000.

**Suggested fix:** Use the per-window fetch approach from `17aac4b`.

### PFI-3: return_pct Naming Ambiguity (Decimal vs Percent)

**Severity:** MUST FIX  
**File:** `market_radar/shared/event_price_backfill.py`  
**Field:** `WindowReturn.return_pct`

**Integration branch (`7934b27`):**  
`return_pct` is calculated as `(target_price / t0_price) - 1.0`, which produces a decimal fraction (`0.007353` for 0.7353%), NOT a percentage. The field name `pct` is misleading — every consumer would interpret it as 0.7353% when the actual value is 0.007353.

**IO RC fix (`17aac4b`):**  
Renamed to `return_decimal` (0.007353) and added `return_percent` (0.7353), both clearly documented. This eliminates ambiguity.

**Suggested fix:** Use the IO RC naming. If the naming must be backward-compatible, at minimum add a docstring clarifying the unit.

---

## 3. Acceptable v1 Limitations

### AL-1: Future Event Timestamps Downgraded (Not Rejected)

**File:** `market_radar/shared/noise_gate.py:122-132`  
**Function:** `_eval_stale_event()`  
**Behavior:** Future timestamps (`age_hours < 0`) return `GateVerdict.DOWNGRADE` with reason `timezone_or_future_timestamp`.

**Assessment:** This is an intentional design choice — a future timestamp may be a legitimate TZ issue, not a fabricated event. The DOWNGRADE verdict means the signal still passes but with reduced confidence. This is acceptable for v1. If future timestamps prove to be a real attack vector, a config flag could upgrade this to REJECT in v1.1.

### AL-2: evaluate_event_semantics() Still Uses 48h Observation Window

**File:** `market_radar/shared/event_intelligence_semantics.py:284-309`  
**Function:** `evaluate_event_semantics()`  
**Window values:** "24h" for high intensity, "48h" for default and no-asset events

**Assessment:** The production path through `EventIntelligenceMapper._get_observation_window()` only uses `VALID_WATCH_WINDOWS = {"1h", "4h", "24h"}`. The 48h in `evaluate_event_semantics()` is only reachable if code calls it directly (as the IO demo does). In the integrated pipeline, the mapper is the entry point and enforces 1h/4h/24h. This is acceptable for v1 but the standalone function should be updated in v1.1 for consistency.

### AL-3: AIInterpreter Stub Always Returns Template

**File:** `market_radar/shared/ai_fallback.py:236-253`  
**Function:** `AIInterpreter._ai_interpret()`  
**Behavior:** Always returns template even when `available=True`.

**Assessment:** The AI interpreter is explicitly designed as a stub/future placeholder. The orchestrator works correctly with template fallback. This is documented in the pre-integration review (P1-4). Acceptable for v1 as long as no production code sets `available=True` expecting real AI output.

### AL-4: Price Backfill Not Yet Integrated into Signal Spine Pipeline

**File:** `market_radar/shared/event_intelligence_mapper.py`  
**Function:** `EventIntelligenceMapper.map_result()`

**Assessment:** The mapper currently does not call `EventPriceBackfill` at any point. Price return data is not available for decision-making. This is acceptable for v1 because:
1. The mapper's four decision categories (OBSERVE/RISK_TIP/BLOCK/DISCARD) work correctly without price data
2. The noise gate's 10 rules cover the main risk categories without requiring price returns
3. Price backfill integration (calling it before the mapper) is a clear v1.1 enhancement

### AL-5: Binance 24h 1m Kline with limit=1000 Workaround

**File:** `market_radar/shared/event_price_backfill.py` (IO RC, not yet integrated)  
**Function:** `fetch_klines_window()`

**Assessment:** The IO RC already implements per-window fetches with small limits, completely avoiding the Binance 1000-limit issue. This is acceptable for v1 as long as the IO RC version (17aac4b) is merged, not the original 7934b27 version.

### AL-6: Fresh Clone Demo UnicodeEncodeError on Windows/GBK

**File:** `scripts/run_signal_spine_v1_demo.py:302,681`  
**Issue:** `print()` with Unicode characters (`✓`, `🎉`) fails on Windows with GBK encoding.

**Assessment:** This is a platform issue in the demo script, not the business logic. The demo correctly passes all 6/6 checks — the UnicodeError causes exit code 1 only because `print()` raises after all checks pass. Fixable by replacing Unicode chars with ASCII equivalents. Not a blocker for v1.

---

## 4. False Positives

### FP-1: event_dedup_key Permanent Merge Across Dates

**Claim:** Same-title different-date events get permanently merged.  
**Verdict:** ✅ FALSE POSITIVE — FIXED

**Evidence:** The integration branch's `Observation._compute_event_dedup_key()` now includes a `_compute_time_bucket(event_time, bucket_hours=24)` component. The `from_normalized_signal()` method passes `event_time or signal.timestamp` to the dedup key computation. Two events with the exact same title/assets/event_type but different dates will produce different time buckets and thus different dedup keys. Test `TestRcTimeBucket::test_same_title_different_day_not_merged` validates this.

**Note:** The time bucket defaults to `bucket_hours=24`, meaning same-day events with the same title still merge. This is intentional behavior for cross-source dedup within the same day.

### FP-2: Pump REJECT Maps to Generic DISCARD

**Claim:** Pump rejection from the noise gate gets lost in a generic "rejected" → DISCARD mapping.  
**Verdict:** ✅ FALSE POSITIVE — FIXED

**Evidence:** The `EventIntelligenceMapper._map_rejected()` has priority-ordered rules. The first check is for `high_chase_or_pump_risk` with `GateVerdict.REJECT`, which maps to `IntelligenceDecision.BLOCK` (禁止). This is the highest priority check, above stale/source/default DISCARD. Test `TestRcPumpMapsToBlock::test_pump_reject_maps_to_block` validates this.

Flow: Gate rejects pump → mapper checks pump first → returns BLOCK.

### FP-3: Fixture Marked REAL in Mapper

**Claim:** Fixture data gets marked as REAL in the event intelligence mapper.  
**Verdict:** ✅ FALSE POSITIVE — PROPERLY HANDLED

**Evidence:** `EventIntelligenceMapper._resolve_data_origin()` uses a priority chain:
1. If `result.data_origin` is set by pipeline → use it
2. If not, check `obs.source_type` → if "fixture" → FIXTURE
3. If "api" or "source" → check `api_success` flag → REAL or DEGRADED
4. Default → FIXTURE (safe default)

The source_type from the adapter properly propagates: fixture adapters set `source_type=FIXTURE`, which the mapper detects and preserves. Only if `source_type` is somehow wrong would the origin be incorrect.

---

## 5. Verified Claims Map

| # | Claim | Code File | Verification | Status |
|---|-------|-----------|-------------|--------|
| 1 | Pump REJECT → BLOCK vs DISCARD | `event_intelligence_mapper.py:97-113` | Mapper has highest-priority pump→BLOCK path | ✅ **BLOCK** |
| 2 | Fixture marked REAL in mapper | `event_intelligence_mapper.py:285-305` | source_type chack preserves FIXTURE | ✅ **FALSE POSITIVE** |
| 3 | DataOrigin defined in both models.py and semantics | `models.py`, `event_intelligence_semantics.py` | Both files now define `DataOrigin` identically | ✅ **FIXED** |
| 4 | 48h/72h observation window | `event_intelligence_semantics.py:284,309` vs `event_intelligence_mapper.py:340-347` | Semantics: 48h present. Mapper: 1h/4h/24h only | ⚠️ **ACCEPTABLE** |
| 5 | event_dedup_key permanent merge across dates | `models.py:462-515` | Time bucket included; same-title different-date → different key | ✅ **FALSE POSITIVE** |
| 6 | Fresh clone complete | `test_signal_spine_io_v1.py:OfflineFreshClone` | 4 tests pass, demo works offline (GBK error only) | ✅ **WORKS** |
| 7 | UTC string vs epoch consistency | `test_event_price_backfill_v1.py:TestFixtureTimestampConsistency` | 3 tests pass, ref_time=1781524800000 verified | ✅ **CONSISTENT** |
| 8 | Partial fixture 1h mature, 4h/24h pending | `event_price_backfill.py` + tests | `get_fixture_klines_partial()`, test passes | ✅ **CORRECT** |
| 9 | Network failure → fixture applied to real events | `event_price_backfill.py` (7934b27) | Integration version has silent fixture fallback | ❌ **IO RC FIXED, integration missing** |
| 10 | Price target Kline max time deviation | `event_price_backfill.py:60` | `MAX_PRICE_LAG_SECONDS = 120`, tests verify | ✅ **CORRECT** |
| 11 | 24h 1m Kline Binance limit=1000 | `event_price_backfill.py:241` | Per-window fetch with small limits | ✅ **IO RC WORKAROUNDED** |
| 12 | return_pct decimal vs percent | `event_price_backfill.py:588-589` | Both `return_decimal` and `return_percent` present | ✅ **AMBIGUITY FIXED in IO RC** |

---

## 6. Integration Branch Health Summary

### What's Fixed Since Pre-Integration Review (P0 Issues)

| P0 Issue | Status | How |
|----------|--------|-----|
| P0-1: Two conflicting DataQuality enums | ✅ **FIXED** | Renamed IO's DataQuality → DataOrigin in both files |
| P0-2: Dedup key includes source | ✅ **FIXED** | Separate `event_dedup_key` (no source) + `observation_fingerprint` (with source) |
| P0-3: trading_relevance receives risk_notes[0] | ✅ **FIXED** | `_assess_trading_relevance()` uses asset count + intensity heuristic |
| P0-4: Core merge vs IO discard semantics | ✅ **FIXED** | `EventIntelligenceMapper` unifies decision via `map_result()` |
| P0-5: Registry silent data loss on JSON corruption | ✅ **FIXED** | Backup recovery + atomic write (temp file + rename) |
| P0-6: IO models.py missing Spine models | ✅ **FIXED** | Both branches share same `models.py` via merge |

### What's Still Broken

| Issue | Priority | Detail |
|-------|----------|--------|
| Demo script stale import | **RELEASE BLOCKER** | `import DataQuality` should be `import DataOrigin` |
| Price backfill missing | **RELEASE BLOCKER** | Module exists only on IO branch |
| Price backfill silent fixture fallback | **MUST FIX** | Integration version has no mode system |
| 48h in evaluate_event_semantics() | **ACCEPTABLE** | Not used in production mapper path |
| Unicode demo crash on Windows | **ACCEPTABLE** | Only affects print(), not logic |

### Integration Demo Run Results

Cannot complete — see RCB-1. The IO branch demo (which doesn't import Core/Registry) passes 6/6 checks:
- Section A: Adapter contract ✅
- Section B: Real adapters ✅
- Section C: Event intelligence ✅
- Section D: Dry-run renderer ✅
- Section E: Golden JSON ✅
- Section F: No real send ✅

---

## 7. Final Acceptance Checklist

| # | Gate | Criterion | Status |
|---|------|-----------|--------|
| 1 | **Demo runs** | `python scripts/run_signal_spine_v1_demo.py --fixture --dry-run` exits 0 | ❌ **BLOCKED** (RCB-1) |
| 2 | **All 126 tests pass** | `python -m pytest tests/ -v` | ✅ **PASS** (126/126) |
| 3 | **Price backfill tests pass** | `python -m pytest tests/test_event_price_backfill_v1.py -v` | ✅ **PASS** (57/57 on IO branch) |
| 4 | **Price backfill module merged** | File exists in integration branch | ❌ **BLOCKED** (RCB-2) |
| 5 | **No silent fixture fallback** | `use_fixture=False` correctly returns failed, not fixture | ❌ **BLOCKED** (PFI-1) |
| 6 | **return_pct unambiguous** | Both decimal and percent forms provided | ❌ **BLOCKED** (PFI-3) |
| 7 | **24h kline under limit** | Per-window fetch or explicit limi handling | ✅ **OK** in IO RC (PFI-2) |
| 8 | **DataOrigin consistent** | Both files define same enum | ✅ **PASS** |
| 9 | **Dedup key time-bucketed** | Different dates → different dedup keys | ✅ **PASS** |
| 10 | **Pump → BLOCK** | High pump risk maps to 禁止, not generic DISCARD | ✅ **PASS** |

**Gates passed:** 5/10  
**Gates blocked:** 5/10 (3 release blockers + 2 must-fix)

---

## 8. Blocking Issue

The integration branch `workbench/overnight-signal-spine-v1@f7bf811` has made significant progress since the pre-integration review:

- All 6 P0 findings from the pre-integration review are **FIXED** on this branch
- 126 tests pass (including new cross-module integration tests)
- The `EventIntelligenceMapper` properly bridges Core and IO lanes
- Dedup keys include time buckets to prevent false cross-date merging
- Registry has atomic writes and backup recovery

However, the integration branch **cannot be released** as-is because:

1. **Demo script is broken** (RCB-1) — the import rename `DataQuality`→`DataOrigin` was done in the model files but NOT in the demo script. Every demo run immediately crashes.
2. **Price backfill is missing** (RCB-2) — the entire price backfill module lives only on the IO branch and was never merged in. It needs to be merged using the IO RC version (`17aac4b`), not the original `7934b27`, because the original has the silent fixture fallback issue (PFI-1) and the `return_pct` naming ambiguity (PFI-3).

**Recommended merge sequence after fixing RCB-1:**
1. Fix the demo script import
2. Merge IO branch price backfill at commit `17aac4b` (not `7934b27`)
3. Import and call `EventPriceBackfill` from `event_intelligence_mapper.py` for price-aware decisioning
4. Run full test suite (expected ≥ 183 tests)
5. Run demo script to verify e2e
