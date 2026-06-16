# Signal Spine v1 — Pre-Integration Review

**Auditor:** Architecture Audit & Integration Lead  
**Date:** 2026-06-16  
**Branches Reviewed:**
- Core: `workbench/signal-spine-core-v1` @ `9768868`
- IO: `workbench/signal-spine-io-v1` @ `989e3e1`

**Scope:** Code review of both Signal Spine implementation branches before integration.

---

## Executive Summary

**64 + 33 = 97 tests pass** across both branches. However, **6 P0 findings** exist that would cause data loss, incorrect event aggregation, or false end-to-end if merged without remediation. The two branches were developed independently and **have never been run together** — the IO runner (the supposed "end-to-end" demo) does not import or use any Core Spine module.

---

## P0 — Cannot Ship Without Fixing

### P0-1: Two Conflicting `DataQuality` Enums With the Same Name

| Aspect | Core `models.py` | IO `event_intelligence_semantics.py` |
|--------|-----------------|--------------------------------------|
| Line | `models.py:306` | `event_intelligence_semantics.py:40` |
| Values | `VERIFIED_HIGH`, `VERIFIED_MEDIUM`, `UNVERIFIED`, `LOW_CREDIBILITY`, `UNKNOWN` | `REAL`, `FIXTURE`, `DEGRADED` |
| Import path | `market_radar.shared.models.DataQuality` | `market_radar.shared.event_intelligence_semantics.DataQuality` |

**Impact:** After merge, `from market_radar.shared.models import DataQuality` and `from market_radar.shared.event_intelligence_semantics import DataQuality` import two completely different enums with identical names. Any code that compares `data_quality == DataQuality.REAL` or `data_quality == DataQuality.VERIFIED_HIGH` will silently fail depending on which import wins.

The IO's `EventIntelligenceResult` uses its own `DataQuality` to mark data provenance (real/fixture/degraded). Core's `Observation.data_quality` uses Core's `DataQuality` to rate source credibility (verified/unverified). These are **orthogonal concepts** that must be disambiguated.

**Reproduce:**
```python
from market_radar.shared.event_intelligence_semantics import DataQuality as EIDQ
from market_radar.shared.models import DataQuality as CoreDQ
assert EIDQ.REAL != CoreDQ.VERIFIED_HIGH  # True, but misleading
assert EIDQ.FIXTURE == CoreDQ.VERIFIED_MEDIUM  # False — different enums
```

**Real impact:** After integration, if `evaluate_event_semantics()` is called with a Core `Observation`, the `data_quality` field of `Observation` (which is Core's `VERIFIED_HIGH`) will NOT match IO's `DataQuality.REAL`. The semantic decision layer will default to `DataQuality.DEGRADED`, degrading all signals regardless of actual quality. All pipeline signals become degraded/risk-only.

**Fix:** Rename IO's `DataQuality` to `ProvenanceQuality` or `DataProvenance`:
```python
class ProvenanceQuality(str, Enum):
    REAL = "real"
    FIXTURE = "fixture"
    DEGRADED = "degraded"
```

---

### P0-2: Dedup Key Contains `source`, Preventing Cross-Source Aggregation

**File:** `market_radar/shared/models.py:457` (Core branch)  
**Function:** `Observation.from_normalized_signal()`  
**Line:**
```python
dedup_raw = f"{source}:{title}:{','.join(sorted(assets))}"
dedup_key = sha256_short(dedup_raw, n=12)
```

**Problem:** The `source` field (e.g., "CoinDesk", "Cointelegraph") is part of the dedup key. Two different news outlets reporting the **same event** will produce different `dedup_key` values because they have different `source` values.

**Reproduce:**
```python
obs1 = Observation.from_normalized_signal(signal, source="CoinDesk")
obs2 = Observation.from_normalized_signal(signal, source="Cointelegraph")
assert obs1.dedup_key != obs2.dedup_key  # Different sources, different keys!
# But they represent the same event!
```

**Real impact:** The same SEC announcement reported by 5 sources creates 5 separate Signals, 5 separate cards, and potentially 5 Telegram messages. Cross-source dedup is completely broken. Evidence cannot be aggregated across sources.

The test `test_observation_dedup_key_different_source` (test_signal_spine_core.py:195) **asserts that different sources SHOULD produce different keys** — this is a circular self-verification that validates the bug as a feature.

**Fix:** Remove `source` from dedup key computation. Use only `title` and `assets`:
```python
dedup_raw = f"{title}:{','.join(sorted(assets))}"
```

---

### P0-3: `trading_relevance` Receives `risk_notes[0]` — Metadata Corruption

**File:** `market_radar/shared/signal_orchestrator.py:163-165`  
**Function:** `SignalOrchestrator.process()` (create_signal call)  
**Lines:**
```python
trading_relevance=interpretation.risk_notes[0]
if interpretation.risk_notes else "medium",
```

**Problem:** The `Signal.trading_relevance` field (expected values: `"high"`, `"medium"`, `"low"`, `"none"`) receives the first element of `interpretation.risk_notes`. Risk notes are strings like:
- `"template_generated: no AI model was consulted for this interpretation"`
- `"confidence is heuristic based on event intensity, not market analysis"`

These are NOT valid `trading_relevance` values.

**Reproduce:**
```python
result = orchestrator.process(observation)
print(result.signal.trading_relevance)
# Output: "template_generated: no AI model was consulted..."
# Expected: "high", "medium", "low", or "none"
```

**Real impact:** Every signal created through the orchestrator will have corrupted `trading_relevance` metadata. Downstream components that filter or prioritize by trading relevance will malfunction. This affects all signals, not just edge cases.

**Fix:**
```python
# Use interpretation's relevance assessment, not risk_notes
trading_relevance = observation.normalized_payload.get(
    "trading_relevance",
    interpretation.raw.get("trading_relevance", "medium")
) if hasattr(interpretation, 'raw') else "medium"
```

Or better, add `trading_relevance` to `InterpretationResult` as a proper field.

---

### P0-4: Core Duplicate=Merge vs IO Duplicate=Discard — Semantic Conflict

**Core behavior** (`signal_orchestrator.py:128-147` and `signal_registry.py:345-385`):
- When `dedup_key` already exists in registry → `_append_observation_to_signal()` appends evidence, merges observation IDs
- Returns `registry_action = "merged_into_existing"`
- The existing signal is returned and continues through pipeline

**IO behavior** (`event_intelligence_semantics.py:161-174`):
- When `is_duplicate=True` → returns `IntelligenceDecision.DISCARD`
- Evidence: `"Duplicate event — same dedup_key as previously seen event"`
- No evidence appending, no signal update

**Problem:** These two semantics are contradictory. Core says "merge and continue", IO says "discard and stop." When integrated, the pipeline decision depends on evaluation order. If Core runs first, duplicate observations get merged and the signal proceeds. If the IO EventIntelligence runs and sees `is_duplicate=True`, it marks the output as DISCARD.

**Real impact:** The display pipeline will show BLOCKED/DISCARD for events that Core has already merged. Users see a contradiction: "signal exists" but "output blocked (duplicate)." Half of all duplicate events produce confusing output.

**Fix:** Align on ONE semantic. Recommend: Core's merge approach is correct for intelligence signals (same event from 2 sources should aggregate). IO should only produce DISCARD for **content-level** duplicates (identical article text), not for cross-source event dedup.

---

### P0-5: Registry Silently Discards All Data on JSON Corruption

**File:** `market_radar/shared/signal_registry.py:81-87`  
**Function:** `SignalRegistry._load()`  

```python
except (json.JSONDecodeError, KeyError, ValueError) as e:
    self._signals = {}
    self._observation_to_signal = {}
    self._dedup_to_signal = {}
    import warnings
    warnings.warn(f"SignalRegistry: corrupted storage at {self._storage_path}, starting fresh: {e}")
```

**Problem:** Any JSON decode error, missing key, or value error causes the registry to silently wipe all in-memory signal state and start fresh. No backup, no recovery file, no automatic repair.

**Reproduce:**
```python
# Simulate: write partial/invalid JSON during a crash
storage.write_text('{"signals": [{"signal_id": "abc", "title": "Test",')
registry = SignalRegistry(storage_path=storage)
assert registry.signal_count() == 0  # All data lost!
```

**Real impact:** Any crash during `registry.save()`, any manual editing mistake, or any concurrent write produces a corrupted file. The registry silently loses **all signals** on next load. For a system that runs once an hour, this means up to 1 hour of signal data is permanently lost before the next save overwrites the corrupt backup.

**Fix:** Implement write-to-tempfile-then-rename pattern:
```python
def save(self):
    self._storage_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = self._storage_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(...), encoding="utf-8")
    tmp.replace(self._storage_path)  # Atomic on same filesystem
```

And on load failure, attempt to recover from `.bak`:
```python
backup = self._storage_path.with_suffix(".bak")
if backup.exists():
    # Try loading from backup
    raw = backup.read_text(encoding="utf-8")
```

---

### P0-6: IO `models.py` Is Outdated — Has No Spine Models

**File:** `cei_signal_io/market_radar/shared/models.py`  
**Commit:** `989e3e1`

**Problem:** The IO branch's `models.py` is the **old version** without any Signal Spine models (no `Observation`, `Signal`, `SignalStatus`, `DataQuality`, etc.). It only has the original v1.17 models (`NormalizedSignal`, `CardFamily`, `GateDecision`, etc.).

**Verification:**
```bash
# On IO branch:
grep -c "class Observation" market_radar/shared/models.py  # Returns 0
grep -c "class Signal" market_radar/shared/models.py       # Returns 0
```

**Real impact:** When merging Core and IO, `models.py` will conflict in its entirety. If the merge is done carelessly (e.g., accepting IO's version), all Spine models are lost. The IO branch's `dry_run_renderer.py` and `event_intelligence_semantics.py` don't import Spine models, so this didn't surface in IO testing — but the integration will break immediately.

**Fix:** Before merging, ensure IO branch `models.py` is identical to Core branch `models.py`. The merge strategy for `models.py` should be: **accept Core's version, then verify IO imports work**.

---

## P1 — Should Fix Before Integration

### P1-1: IO Demo Runner Does Not Use Core/Registry

**File:** `cei_signal_io/scripts/run_signal_spine_v1_demo.py:47-65` (imports)  
**Proof:** The runner imports from `models.py`, `adapter_contract.py`, `renderer_contract.py`, `dry_run_renderer.py`, `event_intelligence_semantics.py`. It does NOT import `SignalRegistry`, `SignalOrchestrator`, `DeterministicNoiseGate`, or any Core Spine component.

**Impact:** The IO runner is marketed as "Independent Verification" but it only verifies IO's own code. It's not an end-to-end test — it's a half-pipeline test that never touches Core.

**Fix:** Add a Section G that creates a `SignalOrchestrator` with a temp registry, processes an observation, and verifies the signal flows through to the dry-run renderer.

### P1-2: `DryRunRenderer` Instantiates But Never Calls `CardRenderer`

**File:** `market_radar/shared/dry_run_renderer.py:131-132`
```python
self._card_renderer = CardRenderer()  # Created but never used
```

**File:** `market_radar/shared/dry_run_renderer.py:140-180`, `render()` method builds its own JSON/MD/TG output directly from fixture_data without calling `self._card_renderer.render()`.

**Impact:** The dry-run output is completely independent from `CardRenderer`. If `CardRenderer` changes its formatting, the dry-run output won't reflect it. The two rendering paths will diverge.

**Fix:** In `DryRunRenderer.render()`, generate a `RenderedCard` via `self._card_renderer.render()` and include its output in the dry-run package.

### P1-3: Future Event Timestamps Are Silent-Accepted

**File:** `market_radar/shared/noise_gate.py:122-132`  
**Rule:** `_eval_stale_event()`  
**Lines:**
```python
if age_hours < 0:
    return NoiseGateResult(
        rule_name="stale_or_recycled_event",
        verdict=GateVerdict.ACCEPT,
        reason_code="future_event_time",
        reason=f"Event time is after observation time ({age_hours:.1f}h) — possible TZ diff, accepted.",
        ...
    )
```

**Problem:** When event_time is in the future relative to observed_at, the gate ACCEPTS with "possible TZ diff, accepted." A +2 hour difference is not a timezone issue (max TZ offset is UTC+14). This could be a data corruption or spoofed timestamp. The gate should REJECT or at minimum DOWNGRADE events with event_time > observed_at + 1 hour.

**Impact:** Artificially "future-dated" events (e.g., claiming an event that hasn't happened yet) would pass the gate silently. This could be used to inject fabricated signals with fake timestamps.

**Fix:** Change verdict to `DOWNGRADE` with a stronger reason:
```python
if age_hours < -1:  # More than 1 hour in the future
    verdict = GateVerdict.DOWNGRADE
    reason_code = "future_event_time_suspicious"
```

### P1-4: `_ai_interpret` Stub Defeats Availability Flag

**File:** `market_radar/shared/ai_fallback.py:236-253`
```python
def _ai_interpret(self, observation: Observation) -> InterpretationResult:
    self._fallback_count += 1
    result = generate_template_interpretation(observation)
    result.interpretation_method = "template_generated"
    return result
```

**Impact:** When `AIInterpreter(available=True)`, calling `interpret()` calls `_ai_interpret()`, which still returns template results. The `interpretation_method` is explicitly overwritten to `"template_generated"`. The availability flag literally does nothing — setting it `True` or `False` produces identical behavior.

**Fix:** Make `_ai_interpret()` raise `NotImplementedError` so that future AI integration must override it:
```python
def _ai_interpret(self, observation):
    raise NotImplementedError("AI interpretation not yet implemented")
```

### P1-5: `Observation.from_normalized_signal()` Ignores `assets_affected` Misspelling

**File:** `market_radar/shared/models.py:438`
```python
assets = list(signal.metrics.get("assets_affected", []))
```

**Problem:** Only checks `"assets_affected"`. The `NormalizedSignal` contract uses `"assets"` (plural) for its asset list (see `free_api_adapters.py:148`, `adapter_contract.py:129`). The misspelling `"assets_affected"` is used only by the news adapter (`free_api_adapters.py:826` — but there the key is `"assets_affected"` in the metrics, which IS correct for that path). However, for multi_asset adapters, the assets are under `metrics["assets"]`, not `metrics["assets_affected"]`.

**Impact:** Observations constructed from `MultiAssetMarketSyncFreeApiAdapter` or `PriceOIVolumeAnomalyFreeApiAdapter` will have **empty `affected_assets`** because the adapter stores assets under `metrics["assets"]` but `from_normalized_signal` only checks `metrics["assets_affected"]`.

**Fix:** Check both keys:
```python
assets = list(signal.metrics.get("assets_affected", []) or signal.metrics.get("assets", []))
```

---

## P2 — Should Fix After Integration

| ID | Finding | File | Detail |
|----|---------|------|--------|
| P2-1 | `Observation.as_dict()` inconsistent enum check | `models.py:485` | Uses `isinstance(x, Enum)` instead of `isinstance(x, str)` like `__post_init__`. Inconsistent. |
| P2-2 | `NormalizedSignal.signal_id` is Optional with no generation | `models.py:84` | `signal_id` is `Optional[str] = None` — never auto-generated. Callers who expect a unique ID get None silently. |
| P2-3 | History not validated on deserialization | `signal_registry.py:108-132` | `_dict_to_signal()` creates `StatusTransition` objects but does NOT validate `from_status`/`to_status` against legal transitions. Corrupted history entries are silently accepted. |
| P2-4 | `NoiseGateResult.passed` is True for `DOWNGRADE` | `models.py:516` | `passed = self.verdict in (ACCEPT, DOWNGRADE)`. Semantically, "passed" means "accepted" — DOWNGRADE is not a pass. This conflates two different concepts. |
| P2-5 | Evidence dedup uses `ref` only | `signal_registry.py:358-360` | Evidence dedup only checks `e.ref` in `existing_refs`. Two pieces of evidence with different refs but identical content are both appended. Not a significant risk with SHA-256 refs. |
| P2-6 | No CI/CD integration | Repository root | No `.github/workflows/` directory. All 97 tests are local-only. |
| P2-7 | IO branch missing `fixtures/` and `scripts/run_signal_spine_v1_demo.py` in git? | IO branch | Need to verify these are committed — they appeared as differences in earlier audit. |

---

## False Positives (Checked, Not a Problem)

1. **Suspect: `DataQuality` string comparison in orchestrator** (`signal_orchestrator.py:201`)
   - Checked: `if quality in ("verified_high", "verified_medium"):`
   - Since `DataQuality(str, Enum)` inherits from `str`, `DataQuality.VERIFIED_HIGH == "verified_high"` evaluates `True`. **Not a bug.**
   - But it IS fragile — if `DataQuality` is changed to not inherit from `str`, this breaks silently.

2. **Suspect: `NormalizedSignal.signal_id` vs `Observation.observation_id` confusion**
   - Checked: They are distinct identifiers for different concepts. `NormalizedSignal` exists in the old pipeline; `Observation` in the new. The `observation_id` is always a `uuid4()`. **Not a bug.**

3. **Suspect: Empty `source_refs` in Observation from_normalized_signal**
   - Checked: `signal.source_refs` could be `[]`, but `Observation.source_refs` defaults to `field(default_factory=list)`. **Not a bug** — empty refs are valid.

---

## Missing Tests

| Test | Priority | What Should Be Tested |
|------|----------|----------------------|
| Cross-source dedup integration | P0 | Two observations with same title+assets from different sources produce ONE signal |
| Observation→Signal→RenderedCard end-to-end | P0 | Full pipeline: adapter → Observation → NoiseGate → Signal → CardRenderer → output |
| Registry recovery from corruption | P0 | Corrupted JSON file does not lose data (backup restored) |
| Signal+Render integration | P0 | `Signal.renderer_payload` is actually used by `CardRenderer` to produce correct output |
| DataQuality→ProvenanceQuality bridge | P0 | Observation with VERIFIED_HIGH produces ProvenanceQuality.REAL in event intelligence |
| `trading_relevance` value integrity | P1 | All signals have valid `trading_relevance` values after orchestration |
| Concurrent save safety | P1 | Registry.save() is safe under concurrent/crash conditions |
| Cross-adapter Observation assets | P1 | Both `metrics["assets"]` and `metrics["assets_affected"]` are handled |
| IO demo runner with Core import | P1 | `run_signal_spine_v1_demo.py --core` runs full combined pipeline |
| Golden JSON stability with Signal | P2 | Golden reference for Signal output, not just NormalizedSignal |

---

## Recommended Acceptance Gates

Before the integration branch `workbench/overnight-signal-spine-v1` can be considered complete, these checks must pass:

### Gate 1: DataQuality Disambiguation
```python
# Must NOT conflict
from market_radar.shared.models import DataQuality as CoreDQ
from market_radar.shared.event_intelligence_semantics import ProvenanceQuality  # renamed
assert CoreDQ.VERIFIED_HIGH.value == "verified_high"
assert ProvenanceQuality.REAL.value == "real"
# Two different types with two different names
```

### Gate 2: Cross-Source Dedup Works
```python
signal = NormalizedSignal(..., metrics={"title": "SEC ETF", "assets_affected": ["BTC"]})
obs1 = Observation.from_normalized_signal(signal, source="CoinDesk")
obs2 = Observation.from_normalized_signal(signal, source="Cointelegraph")
assert obs1.dedup_key == obs2.dedup_key  # Same event, same key
```

### Gate 3: `trading_relevance` Is Valid
```python
result = orchestrator.process(observation)
assert result.signal.trading_relevance in ("high", "medium", "low", "none")
assert not result.signal.trading_relevance.startswith("template_generated")
```

### Gate 4: Registry Write Is Atomic
```python
storage = Path("test_atomic_registry.json")
registry = SignalRegistry(storage_path=storage)
# ... add some signals ...
registry.save()
# Power loss during save → no data loss
import json, os
backup = storage.with_suffix(".bak")
assert backup.exists() or os.path.getsize(storage) > 100  # recovery path
```

### Gate 5: IO Demo Runs Full Pipeline
```bash
python scripts/run_signal_spine_v1_demo.py --core  # Uses SignalOrchestrator internally
# Reports: Core: created/merged signals, IO: dry-run render complete
```

### Gate 6: All 97 + New Tests Pass
```bash
python -m pytest tests/ -v
# Must show all existing + new tests passing
# 64 (core) + 33 (io) + (new cross-module tests) ≥ 100
```

### Gate 7: `models.py` Is Identical on Both Branches at Merge Point
```bash
diff -q market_radar/shared/models.py <(cd ..io && git show HEAD:market_radar/shared/models.py)
# Should show no differences OR explicitly resolved differences
```

---

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| P0-1 | **BLOCKER** | `event_intelligence_semantics.py:40` | Two `DataQuality` enums with same name, different values |
| P0-2 | **BLOCKER** | `models.py:457` | Dedup key includes `source`, prevents cross-source aggregation |
| P0-3 | **BLOCKER** | `signal_orchestrator.py:164` | `trading_relevance` receives risk_notes[0], corrupting metadata |
| P0-4 | **BLOCKER** | Both branches | Core merge vs IO discard — contradictory duplicate semantics |
| P0-5 | **BLOCKER** | `signal_registry.py:81-87` | Corrupted JSON silently drops all signals; no atomic write |
| P0-6 | **BLOCKER** | IO `models.py` | IO branch models.py has NO Spine models — merge will conflict |
| P1-1 | HIGH | IO demo runner | Never imports or uses Core/Registry |
| P1-2 | HIGH | `dry_run_renderer.py:131` | `CardRenderer` instantiated but never called |
| P1-3 | HIGH | `noise_gate.py:122-132` | Future event timestamps silent-accepted |
| P1-4 | MEDIUM | `ai_fallback.py:236-253` | `available=True` has no effect |
| P1-5 | MEDIUM | `models.py:438` | Ignores `metrics["assets"]` (plural), only checks `"assets_affected"` |
| P2-1 | LOW | `models.py:485` | Inconsistent enum check in `as_dict()` |
| P2-2 | LOW | `models.py:84` | `signal_id` never auto-generated |
| P2-3 | LOW | `signal_registry.py:108-132` | History not validated on deserialization |
| P2-4 | LOW | `models.py:516` | `passed=True` for DOWNGRADE — conflates concepts |
