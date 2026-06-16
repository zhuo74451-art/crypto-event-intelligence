# Signal Spine v1 — Repository Audit Report

**Auditor:** Architecture Audit & Integration Lead  
**Date:** 2026-06-16  
**Branch:** workbench/signal-spine-audit-v1  
**Starting Commit:** `37b9c9b8963a4224a74d276077e6df606bbeaf4a`  
**Pipeline Version in Code:** v1.17 (PIPELINE_VERSION)

---

## 1. Current State: Is There an End-to-End Pipeline?

**YES — but with critical caveats.**

The committed code in `market_radar/shared/pipeline.py` contains a working `SharedPipeline` class that chains:

```
adapter → QualityGate → renderer → SendReadinessGate → TGTestGroupSender → EvidenceLedger
```

**Evidence:**
- `market_radar/shared/pipeline.py:56-136` — `SharedPipeline.run()` implements the full 6-stage pipeline
- `market_radar/shared/pipeline.py:138-145` — `run_all_fixtures()` runs all 5 card families
- `market_radar/shared/pipeline.py:148-174` — `run_real_free_api()` runs real Binance adapters
- `market_radar/shared/pipeline.py:177-199` — `run_pipeline()` convenience function

**Caveats:**
1. This pipeline operates on **NormalizedSignal**, not on an Observation/Signal model
2. The pipeline has NO dedup layer — each run creates fresh signals
3. The pipeline has NO signal lifecycle management
4. The pipeline is designed for one-shot demo runs, not continuous monitoring
5. Real TG send requires env vars that may not be configured

---

## 2. Observation Model Status

**DOES NOT EXIST in committed code.**

The committed `market_radar/shared/models.py` does NOT contain an `Observation` class. It defines:
- `NormalizedSignal` — line 62: the current unified signal format
- `GateDecision` — line 96
- `RenderedCard` — line 142
- `TGTestSendResult` — line 181
- `EvidenceRecord` — line 209
- `SharedPipelineResult` — line 238

**Uncommitted Reference:** `cei_signal_core/market_radar/shared/signal_registry.py:24` imports `Observation` and `Signal` from `market_radar.shared.models`, but these classes do not exist in the committed models.py. The `Observation` model must be created as part of Signal Spine.

**Also in IO worktree:** `cei_signal_io/market_radar/shared/event_intelligence_semantics.py:48` defines `EventIntelligenceResult` — a semantic decision wrapper, not an Observation.

---

## 3. Signal Object Status

**DOES NOT EXIST in committed code.**

No `Signal` class, `SignalStatus` enum, or `EvidenceLink` class exists in the committed `models.py`. These are referenced but not defined:

- `market_radar/shared/models.py` — expected to add: `Observation`, `Signal`, `SignalStatus`, `EvidenceLink`, `NoiseGateResult`, `GateVerdict`, `StatusTransition`, `SIGNAL_SPINE_VERSION`, `ObservationStatus`

**Uncommitted code depends on these** — `signal_registry.py`, `noise_gate.py`, `signal_orchestrator.py` all import Signal Spine models that don't exist yet.

---

## 4. Registry / Ledger / Persistence Layer

| Component | Status | File |
|-----------|--------|------|
| `EvidenceLedger` | ✅ COMMITTED — records pipeline run evidence | `shared/evidence_ledger.py` |
| `SignalRegistry` | ⚠️ UNCOMMITTED — in core worktree only | `cei_signal_core/shared/signal_registry.py` |
| **Card Type Registry** | ✅ COMMITTED — static card type definitions | `scripts/market_radar_card_type_registry_v112a.py` |
| **Dedupe Gate** | ✅ COMMITTED — dedup+cooldown gate logic | `scripts/market_radar_dedupe_cooldown_gate_v112i.py` |
| **Source Registry** | ⚠️ REFERENCED as CSV | `data/source_registry.csv` (not audited) |

**Key finding:** The `EvidenceLedger` (evidence_ledger.py) can record pipeline execution metadata but **CANNOT** serve as a Signal Registry. It records one entry per pipeline run with `card_family`, `timestamp`, `quality_gate_allow`, `tg_status`, and a redacted `proof`. It has no:
- Signal CRUD operations
- Evidence appending
- Status transitions
- Dedup key tracking
- Query/filter capabilities

The uncommitted `SignalRegistry` adds all of these, but it's not in the committed codebase.

---

## 5. Deduplication Architecture

**Two layers exist in committed code (plus one uncommitted):**

### Layer 1: Script-level Dedup Cooldown Gate
- **File:** `scripts/market_radar_dedupe_cooldown_gate_v112i.py`
- **Key function:** `check_dedupe()` — line 189: matches `dedupe_key` string against `prior_state`
- **Key function:** `check_cooldown()` — line 229: matches `cooldown_key` + expiration check
- **Key:** `dedupe_key` — an opaque string (likely hash) from signal envelope
- **Status:** ✅ COMMITTED but as a script, not integrated into pipeline

### Layer 2: Script-level Event Candidates Dedup
- **File:** `scripts/deduplicate_event_candidates.py`
- **Key function:** `cluster_key()` — line 40: `sha1(entity|event_type|time_bucket)`
- **Key:** Composite of `primary_entity + event_type + 2-hour time window`
- **Status:** ✅ COMMITTED but for CSV-based pipeline, not shared pipeline

### Layer 3 (Uncommitted): Noise Gate Dedup
- **File:** `cei_signal_core/market_radar/shared/noise_gate.py`
- **Key function:** `_eval_duplicate_event()` — line 44: checks `obs.dedup_key` against `known_dedup_keys` set
- **Status:** ⚠️ UNCOMMITTED — part of Signal Spine work

### Shared Pipeline's QualityGate
- **File:** `shared/gate_contract.py`
- **Key function:** `QualityGate.evaluate()` — line 54
- **Does NOT perform dedup** — it only evaluates signal quality per card family rules

**Summary:** Dedup is fragmented across script-level tools and uncommitted new code. The shared pipeline (`shared/pipeline.py`) has no dedup step.

---

## 6. Gate Architecture

### Current: `QualityGate` is a REAL pipeline barrier (class-based)
- **File:** `shared/gate_contract.py:38-225`
- **Class:** `QualityGate` with `evaluate(NormalizedSignal) → GateDecision`
- **Five per-card-family evaluators** with distinct rules
- **Status:** ✅ COMMITTED and integrated into SharedPipeline

### Current: `SendReadinessGate` is a REAL pipeline barrier
- **File:** `shared/gate_contract.py:233-288`
- **Class:** `SendReadinessGate` with `evaluate(RenderedCard, GateDecision) → SendReadinessDecision`
- **Status:** ✅ COMMITTED and integrated into SharedPipeline

### New (uncommitted): `DeterministicNoiseGate`
- **File:** `cei_signal_core/market_radar/shared/noise_gate.py:750-815`
- **Class:** `DeterministicNoiseGate` with `evaluate(Observation) → list[NoiseGateResult]`
- **10 rules** including dedup, staleness, tradable asset, source quality, material expectation, price-in, overcrowding, social heat, pump risk
- **Status:** ⚠️ UNCOMMITTED — intended to sit between adapter and signal creation

**Summary:** The committed pipeline has two real class-based gates. The uncommitted Signal Spine adds a new gate (`DeterministicNoiseGate`) that would sit in a different architectural position (before signal creation vs. before card rendering).

---

## 7. Signal Lifecycle / Status

**NO lifecycle exists in committed code.**

The uncommitted `Signal` model (referenced by `signal_registry.py`, not yet defined in `models.py`) is expected to have these statuses:

| Status | Meaning |
|--------|---------|
| `CANDIDATE` | Initial state — signal created from observation |
| `ACTIVE` | Passed initial gates, being monitored |
| `WATCHING` | Active with extended observation window |
| `CONFIRMED` | Multiple corroborating observations |
| `EXPIRED` | Time window passed without confirmation |
| `INVALIDATED` | Explicitly invalidated (with invalidation_reason) |

The committed pipeline creates `NormalizedSignal` → `GateDecision` → `RenderedCard` → `EvidenceRecord` in a single synchronous flow with no lifecycle concept.

---

## 8. Evidence Ledger Capabilities

**Can the current `EvidenceLedger` serve as signal version/evidence/audit layer?**

| Capability | EvidenceLedger | SignalRegistry (uncommitted) |
|------------|---------------|---------------------------|
| Record pipeline entry | ✅ ONE entry per run | ✅ Multiple evidence links per signal |
| Proof/redaction | ✅ SHA-256 fingerprint | ✅ SHA-256 fingerprint |
| Audit trail | ❌ One-shot, no history | ✅ Full StatusTransition history |
| Evidence appending | ❌ No append API | ✅ `append_evidence()` |
| Signal CRUD | ❌ Not applicable | ✅ `create_signal()`, `get_signal()` |
| Dedup tracking | ❌ Not present | ✅ `dedup_to_signal` map |
| Query/filter | ❌ Not present | ✅ `query_signals()` with filters |
| State transitions | ❌ Not present | ✅ `transition_status()` with validation |
| Confidence updates | ❌ Not present | ✅ `update_confidence()` with recording |

**Conclusion:** The current `EvidenceLedger` is a **pipeline execution log**, not a signal registry. It CANNOT serve as the Signal Registry for Signal Spine. However, it should be **extended** or **wrapped** — not replaced — since it already handles redaction and JSONL output.

---

## 9. Binance & Free Data Output

### Binance — `MultiAssetMarketSyncFreeApiAdapter`
- **File:** `shared/free_api_adapters.py:60-158`
- **Output:** `NormalizedSignal` with `metrics.assets[]` (BTC/ETH/SOL ticker data)
- **Status:** ✅ COMMITTED and working

### Binance — `PriceOIVolumeAnomalyFreeApiAdapter`
- **File:** `shared/free_api_adapters.py:166-281`
- **Output:** `NormalizedSignal` with `metrics.signals[]` (price+OI anomaly detection)
- **Status:** ✅ COMMITTED and working

### Free Public Sources — `NewsEventMarketImpactFreePublicSourceAdapter`
- **File:** `shared/free_api_adapters.py:443-854`
- **Output:** `NormalizedSignal` with `metrics.title, metrics.event_type, metrics.intensity`, etc.
- **Status:** ✅ COMMITTED and working (RSS-based, no API key)

### Hyperliquid (IO worktree only)
- **File:** `cei_signal_io/market_radar/shared/hyperliquid_info_adapter.py`
- **Output:** Unknown without reading — but NOT registered in `REAL_FREE_API_ADAPTERS`
- **Status:** ⚠️ UNCOMMITTED — standalone, not integrated

**All committed adapters produce `NormalizedSignal`**, never `Observation`. The Signal Spine needs these adapters to produce `Observation` objects instead (or a conversion layer).

---

## 10. Renderer & Dry-Run Status

### Committed: `CardRenderer`
- **File:** `shared/renderer_contract.py:25-281`
- **Output:** `RenderedCard` with title, body, risk_disclaimer, evidence_summary
- **All 5 card families** have dedicated renderers
- **Status:** ✅ COMMITTED and integrated into pipeline

### Committed: `TGTestGroupSender`
- **File:** `shared/sender_contract.py:121-469`
- **Features:** TG test group send, redacted proofs, network error classification, proxy detection
- **Status:** ✅ COMMITTED and integrated into pipeline

### IO Worktree: `DryRunRenderer`
- **File:** `cei_signal_io/market_radar/shared/dry_run_renderer.py:124-419`
- **Output:** `DryRunOutput` with JSON + Markdown + Telegram-style card
- **Overlays** `EventIntelligenceResult` (观察/风险提示/禁止/丢弃) on top of CardRenderer
- **Status:** ⚠️ UNCOMMITTED — standalone, not integrated into pipeline

### IO Worktree: `EventIntelligenceResult`
- **File:** `cei_signal_io/market_radar/shared/event_intelligence_semantics.py:48-119`
- **Decisions:** 观察(OBSERVE), 风险提示(RISK_TIP), 禁止(BLOCK), 丢弃(DISCARD)
- **Status:** ⚠️ UNCOMMITTED — semantically different from the current pipeline's GateDecision

---

## 11. Test Baseline

### Commit-level tests:
- **Total:** Only 2 test files under `tests/`
  - `tests/test_cn_number_formatters.py` — Chinese number formatting regression
  - `tests/test_position_pnl_consistency.py` — PnL sign consistency
- **No tests for shared pipeline**, models, contracts, or evidence ledger

### Script-level "tests":
- `scripts/` contains ~100+ `test_*.py` and `run_market_radar_v*.py` files
- These are **integration runners**, not unit tests (no pytest asserts)
- Many generate CSV/markdown output rather than pass/fail
- Status: **NOT reliable as test baseline**

### IO Worktree test:
- `cei_signal_io/tests/test_signal_spine_io_v1.py` — pytest-based tests for IO components
- **Status:** ⚠️ UNCOMMITTED

---

## 12. Signal Spine — Gap Analysis

From the Signal Spine v1 architecture (as inferred from uncommitted code and Notion documentation):

| Component | Status | Evidence |
|-----------|--------|----------|
| `Observation` model | ❌ MISSING | Not in committed models.py |
| `Signal` model | ❌ MISSING | Not in committed models.py |
| `SignalStatus` lifecycle | ❌ MISSING | Not in committed models.py |
| `SIGNAL_SPINE_VERSION` | ❌ MISSING | Not in committed models.py |
| `EvidenceLink` | ❌ MISSING | Not in committed models.py |
| `NoiseGateResult` | ❌ MISSING | Not in committed models.py |
| `GateVerdict` | ❌ MISSING | Not in committed models.py |
| `StatusTransition` | ❌ MISSING | Not in committed models.py |
| `DeterministicNoiseGate` | ⚠️ UNCOMMITTED | In core worktree only |
| `SignalRegistry` | ⚠️ UNCOMMITTED | In core worktree only |
| `SignalOrchestrator` | ⚠️ UNCOMMITTED | In core worktree only |
| `AIInterpreter` | ⚠️ UNCOMMITTED | In core worktree only |
| `EventIntelligenceResult` | ⚠️ UNCOMMITTED | In IO worktree only |
| `DryRunRenderer` | ⚠️ UNCOMMITTED | In IO worktree only |
| `HyperliquidInfoFreeApiAdapter` | ⚠️ UNCOMMITTED | In IO worktree only |
| Fixture files (IO) | ⚠️ UNCOMMITTED | In IO worktree only |
| Signal Spine v1 demo runner | ⚠️ UNCOMMITTED | In IO worktree only |

### Actually existing and committed:
| Component | File |
|-----------|------|
| `NormalizedSignal` (predecessor) | `shared/models.py:62` |
| `CardFamily` | `shared/models.py:41` |
| `DataSourceType` | `shared/models.py:50` |
| `SignalAdapter` (contract) | `shared/adapter_contract.py:35` |
| `FixtureSignalAdapter` | `shared/adapter_contract.py:69` |
| `FixtureCatalog` | `shared/adapter_contract.py:103` |
| `QualityGate` | `shared/gate_contract.py:38` |
| `SendReadinessGate` | `shared/gate_contract.py:233` |
| `CardRenderer` | `shared/renderer_contract.py:25` |
| `TGTestGroupSender` | `shared/sender_contract.py:121` |
| `EvidenceLedger` | `shared/evidence_ledger.py:29` |
| `SharedPipeline` | `shared/pipeline.py:56` |
| Multi-asset Binance adapter | `shared/free_api_adapters.py:60` |
| Price/OI anomaly adapter | `shared/free_api_adapters.py:166` |
| News event public source adapter | `shared/free_api_adapters.py:443` |

---

## 13. Notion v0.2 Event Intelligence vs. Code Semantics

The Notion v0.2 describes "Event Intelligence" as a system that:

1. **Observes events** — Not observation "为什么涨跌"，而是 event 发生了，观察到市场反应
2. **Decides what to do** — 观察/风险提示/禁止/丢弃 (4 categories)
3. **Never trades** — No buy/sell/long/short

**Conflict with current code:**

| Notion v0.2 Concept | Current Code Equivalent | Semantic Gap |
|---------------------|------------------------|--------------|
| Event Observation | `NormalizedSignal` | Signal is a price/volume data point, not an observed event |
| Event Intelligence decision | `GateDecision` (allow/block) | Binary quality check vs. 4-category semantic decision |
| Signal | `NormalizedSignal` → `RenderedCard` | No persistent signal object with lifecycle |
| Registry | `EvidenceLedger` | Execution log vs. signal management |
| 观察/风险提示/禁止/丢弃 | Not implemented in pipeline | Only exists as `EventIntelligenceResult` (uncommitted) |

**The uncommitted IO worktree's `event_intelligence_semantics.py`** bridges this gap by implementing the 4-category decision system, but it's not wired into the pipeline.

---

## 4. Duplicate/Conflicting Code

### `cei_signal_core` vs `cei_signal_io` — Divergent Working Trees

Both are checked out at the same commit (`37b9c9b`) but contain different uncommitted files:

**Unique to `cei_signal_core` (Signal Spine Core work):**
- `market_radar/shared/signal_registry.py`
- `market_radar/shared/signal_orchestrator.py`
- `market_radar/shared/noise_gate.py`
- `market_radar/shared/ai_fallback.py`

**Unique to `cei_signal_io` (Signal Spine IO work):**
- `market_radar/shared/dry_run_renderer.py`
- `market_radar/shared/event_intelligence_semantics.py`
- `market_radar/shared/hyperliquid_info_adapter.py`
- `fixtures/` directory (8 fixture files + loader + golden)
- `scripts/run_signal_spine_v1_demo.py`
- `tests/test_signal_spine_io_v1.py`
- `docs/signal_spine_io_v1_verification.md`

### Script-level Redundancies

The `scripts/` directory contains multiple versions of similar concepts:
- `market_radar_quality_gate_v117.py` and `shared/gate_contract.py` — both define quality gates
- `market_radar_renderer_contract_v117.py` and `shared/renderer_contract.py` — both define renderers
- `market_radar_send_readiness_gate_v117.py` and `shared/gate_contract.py` — both define send-readiness
- `market_radar_evidence_ledger_v117.py` and `shared/evidence_ledger.py` — both define evidence ledgers

The `shared/` versions are the canonical ones. The `scripts/market_radar_*_v117.py` files appear to be predecessors or standalone copies.

### Historical vs. Shared Pipeline

The entire `scripts/` directory (~200+ files) represents a **v0.6-v1.16 historical pipeline** based on CSV files and pandas. The `market_radar/shared/` directory (9 files) represents the **v1.17 shared pipeline** with proper Python classes. These are parallel systems that don't call each other.

---

## Appendix A: Directory Structure Summary (Committed)

```
market_radar/shared/          ← Canonical pipeline code (9 files)
  __init__.py
  adapter_contract.py         ← SignalAdapter, FixtureSignalAdapter, FixtureCatalog
  evidence_ledger.py          ← EvidenceLedger (pipeline execution log)
  free_api_adapters.py        ← Binance + news public API adapters
  gate_contract.py            ← QualityGate, SendReadinessGate
  models.py                   ← NormalizedSignal, CardFamily, etc.
  pipeline.py                 ← SharedPipeline orchestrator
  renderer_contract.py        ← CardRenderer
  sender_contract.py          ← TGTestGroupSender

scripts/                      ← Historical pipeline + test runners (~200 files)
tests/                        ← Only 2 regression test files
docs/                         ← Claude prompts, runbooks, no architecture docs
fixtures/                     ← (empty in core, has files in IO)
config/                       ← Configuration
data/                         ← CSV data files
```

## Appendix B: Key Test Runners (committed)

- `scripts/run_market_radar_v117_shared_pipeline_real_one_shot.py` — runs the committed shared pipeline with real Binance data
- `scripts/run_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py` — pipeline + TG one-shot
- `scripts/run_market_radar_v118b_five_card_operator_snapshot_with_blocked_gate_overlay.py` — all 5 families
- `scripts/run_market_radar_v119c_mvp_seal_user_demo_pack.py` — latest demo pack
