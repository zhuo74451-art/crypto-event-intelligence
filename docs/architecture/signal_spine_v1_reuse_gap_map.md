# Signal Spine v1 — Reuse & Gap Map

**Purpose:** Map which existing components can be reused for Signal Spine, and what is truly missing.

---

## 1. Layers That Can Be Reused DIRECTLY (no changes needed)

| Existing Component | File | Use in Signal Spine | Confidence |
|-------------------|------|-------------------|------------|
| `CardFamily` enum | `shared/models.py:41` | Canonical card family taxonomy | HIGH |
| `DataSourceType` enum | `shared/models.py:50` | Source type classification | HIGH |
| `SignalAdapter` ABC | `shared/adapter_contract.py:35` | Base class for all adapters | HIGH |
| `FixtureSignalAdapter` | `shared/adapter_contract.py:69` | Test/fixture adapter for any model | HIGH |
| `FixtureCatalog` | `shared/adapter_contract.py:103` | Pre-built fixture data source | HIGH |
| `MultiAssetMarketSyncFreeApiAdapter` | `shared/free_api_adapters.py:60` | Real Binance adapter → produces Observation | HIGH |
| `PriceOIVolumeAnomalyFreeApiAdapter` | `shared/free_api_adapters.py:166` | Real Binance adapter → produces Observation | HIGH |
| `NewsEventMarketImpactFreePublicSourceAdapter` | `shared/free_api_adapters.py:443` | Real news adapter → produces Observation | HIGH |
| `REAL_FREE_API_ADAPTERS` | `shared/free_api_adapters.py:861` | Adapter registry to extend | HIGH |
| `create_real_free_api_adapter()` | `shared/free_api_adapters.py:868` | Factory function | HIGH |
| `QualityGate` | `shared/gate_contract.py:38` | Post-signal quality check (adapt to Signal) | MEDIUM |
| `SendReadinessGate` | `shared/gate_contract.py:233` | Pre-send gate for TG | HIGH |
| `CardRenderer` | `shared/renderer_contract.py:25` | Render Signal → RenderedCard | HIGH |
| `TGTestGroupSender` | `shared/sender_contract.py:121` | Send cards to TG test group | HIGH |
| `EvidenceLedger` | `shared/evidence_ledger.py:29` | Pipeline execution log (extend, don't replace) | MEDIUM |
| `sha256_short()` | `shared/models.py:33` | Redacted fingerprint utility | HIGH |
| `china_now()` | `shared/models.py:28` | UTC+8 timestamp utility | HIGH |
| `PIPELINE_VERSION` | `shared/models.py:25` | Version tracking | HIGH |
| 5 fixture card family data | `shared/adapter_contract.py:123-255` | Test data for all families | HIGH |
| `NormalizedSignal` model | `shared/models.py:62` | Transitional: keep for backward compat, replace for Spine | MEDIUM |

---

## 2. Layers That Need MODIFICATION (extend or adapt)

| Component | File | Required Change | Rationale |
|-----------|------|----------------|-----------|
| `shared/models.py` | All Spine models need to be added here | Add `Observation`, `Signal`, `SignalStatus`, `EvidenceLink`, `NoiseGateResult`, `GateVerdict`, `StatusTransition`, `ObservationStatus`, `SIGNAL_SPINE_VERSION`, `DataQuality` enums | These are the canonical model locations; adding Spine models here keeps a single source of truth |
| `shared/pipeline.py` | `SharedPipeline` class | Add an alternate `process_observation()` path, or create a `SignalSpinePipeline` that uses `SignalOrchestrator` internally | The current pipeline is linear adapter→gate→renderer→send; Signal Spine needs observation→noise_gate→signal→lifecycle→renderer→send |
| `shared/evidence_ledger.py` | `EvidenceLedger` class | Add `append_to_signal()`, `get_history()`, `query_by_signal()` methods | Make it serve as both pipeline log and signal evidence store |
| `shared/free_api_adapters.py` | `create_real_free_api_adapter()` | Add `HyperliquidInfoFreeApiAdapter` to `REAL_FREE_API_ADAPTERS` | After the adapter is committed and verified |
| `shared/adapter_contract.py` | `SignalAdapter` | Optionally add a `to_observation()` method or conversion utility | Allows adapters to produce both NormalizedSignal (backward compat) and Observation |

---

## 3. Layers That Are TRULY MISSING (must be created)

| Component | Priority | Suggested File | Description |
|-----------|----------|---------------|-------------|
| `Observation` model | P0 — BLOCKER | `shared/models.py` | Core data model representing an observed event. Fields: `observation_id`, `dedup_key`, `source`, `source_refs`, `event_time`, `observed_at`, `affected_assets`, `normalized_payload`, `data_quality`, `card_family`, `source_type`, `ingestion_status`, `evidence` |
| `Signal` model | P0 — BLOCKER | `shared/models.py` | Persistent signal object with lifecycle. Fields: `signal_id`, `title`, `affected_assets`, `event_type`, `direction`, `confidence`, `status`, `evidence[]`, `observation_ids[]`, `transition_history[]` |
| `SignalStatus` enum | P0 — BLOCKER | `shared/models.py` | `CANDIDATE`, `ACTIVE`, `WATCHING`, `CONFIRMED`, `EXPIRED`, `INVALIDATED` |
| `EvidenceLink` dataclass | P0 — BLOCKER | `shared/models.py` | Individual evidence entry: `ref`, `source`, `timestamp`, `description`, `ref_type` |
| `NoiseGateResult` dataclass | P0 — BLOCKER | `shared/models.py` | One gate rule evaluation result |
| `GateVerdict` enum | P0 — BLOCKER | `shared/models.py` | `ACCEPT`, `REJECT`, `DOWNGRADE`, `NOT_EVALUATED` |
| `StatusTransition` dataclass | P0 — BLOCKER | `shared/models.py` | Lifecycle transition record |
| `ObservationStatus` enum | P1 | `shared/models.py` | `NEW`, `PROCESSED`, `FAILED` |
| `DataQuality` enum | P1 | `shared/models.py` | `VERIFIED_HIGH`, `VERIFIED_MEDIUM`, `UNVERIFIED`, `LOW_CREDIBILITY`, `UNKNOWN` |
| `SIGNAL_SPINE_VERSION` str | P0 — BLOCKER | `shared/models.py` | Version constant for Signal Spine pipeline |
| `SignalSpineResult` dataclass | P1 | `shared/models.py` | Result of processing an observation through Signal Spine |
| `DeterministicNoiseGate` | P1 | `shared/noise_gate.py` | Already exists in core worktree — commit it |
| `SignalRegistry` | P1 | `shared/signal_registry.py` | Already exists in core worktree — commit it |
| `SignalOrchestrator` | P1 | `shared/signal_orchestrator.py` | Already exists in core worktree — commit it |
| `AIInterpreter` | P2 | `shared/ai_fallback.py` | Already exists in core worktree — commit it |
| `EventIntelligenceResult` | P2 | `shared/event_intelligence_semantics.py` | Already exists in IO worktree — commit it |
| `DryRunRenderer` | P2 | `shared/dry_run_renderer.py` | Already exists in IO worktree — commit it |

---

## 4. Pipeline Integrations Needed

| Integration | Priority | Description |
|-------------|----------|-------------|
| Adapter → Observation | P0 | Adapt current adapters (which produce NormalizedSignal) to also produce Observation, OR create a conversion layer |
| Observation → NoiseGate → Signal | P0 | Wire `SignalOrchestrator.process(observation)` after adapter output |
| Signal → QualityGate | P1 | Adapt `QualityGate.evaluate()` to accept `Signal` in addition to `NormalizedSignal` |
| Signal → CardRenderer | P1 | Adapt `CardRenderer.render()` to accept `Signal` |
| Registry → EvidenceLedger | P1 | `SignalRegistry` uses JSON file; `EvidenceLedger` writes pipeline-level JSONL. Decide which is canonical |
| EventIntelligence → Decision | P2 | Wire `evaluate_event_semantics()` after quality gate for 4-category decision overlay |

---

## 5. Adapter Conversion Strategy

The three committed adapters produce `NormalizedSignal`. For Signal Spine, we need them to produce `Observation`. Two strategies:

**Strategy A: Add `to_observation()` to SignalAdapter (Recommended)**
```python
class SignalAdapter(ABC):
    @abstractmethod
    def fetch(self) -> NormalizedSignal: ...

    def to_observation(self) -> Observation:
        """Convert the latest NormalizedSignal to an Observation."""
        signal = self.fetch()
        # ... conversion logic
```

**Strategy B: Create wrapper adapters**
```python
class ObservationSignalAdapter(SignalAdapter):
    """Wraps any SignalAdapter to produce Observations."""
    def fetch(self) -> NormalizedSignal:
        return self._inner.fetch()

    def fetch_observation(self) -> Observation:
        ns = self.fetch()
        return Observation.from_normalized_signal(ns)
```

**Recommendation:** Strategy A — minimal change, backward compatible, single source of truth.

---

## 6. Registry Persistence Decision

| Aspect | EvidenceLedger | SignalRegistry | Recommendation |
|--------|---------------|----------------|----------------|
| Storage | JSONL file | JSON file | Keep both; different purposes |
| Entries | One per pipeline run | One per signal | SignalRegistry spans multiple runs |
| Redaction | SHA-256 proofs | SHA-256 + structured data | Both handle security |
| Query | None (write-only) | `query_signals()` with filters | SignalRegistry for queries |
| Audit | `verify_no_raw_secrets()` | `transition_history[]` | Combine approaches |

**Decision:** `SignalRegistry` is the canonical registry for Signal Spine. `EvidenceLedger` continues as the pipeline execution audit log. EvidenceLedger should gain an optional link to SignalRegistry entries.

---

## 7. Gate Positioning in New Pipeline

```
Current:  adapter → QualityGate → renderer → SendReadinessGate → sender → ledger

Signal Spine:
  adapter → [to_observation] → DeterministicNoiseGate → SignalRegistry →
    QualityGate → [EventIntelligence] → CardRenderer → SendReadinessGate → sender → ledger
                                    ↘ DryRunRenderer (when dry-run mode)
```

The critical additions are:
1. `to_observation()` — adapter output conversion
2. `DeterministicNoiseGate.evaluate(Observation)` — before signal creation
3. `SignalRegistry.create_signal()` — signal persistence
4. `EventIntelligence` overlay — optional 4-category decision
