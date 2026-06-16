# Signal Spine v1 — Integration Manifest

**Target Branch:** `workbench/overnight-signal-spine-v1` (already reserved — do not create or modify in this audit)  
**Audit Date:** 2026-06-16  
**Audit Commit:** `37b9c9b8963a4224a74d276077e6df606bbeaf4a`

---

## 1. Canonical Modules (Single Source of Truth)

These modules MUST be the single source of truth for their respective concerns. All integration work should reference these files only.

| Module | File | Authority For |
|--------|------|---------------|
| **Models** | `market_radar/shared/models.py` | All data models: `Observation`, `Signal`, `NormalizedSignal`, `CardFamily`, `DataSourceType`, `SignalStatus`, `EvidenceLink`, `NoiseGateResult`, `GateVerdict`, `StatusTransition`, `ObservationStatus`, `DataQuality`, `GateDecision`, `RenderedCard`, `TGTestSendResult`, `EvidenceRecord`, `SharedPipelineResult`, `SignalSpineResult` |
| **Adapter Contract** | `market_radar/shared/adapter_contract.py` | `SignalAdapter` ABC, `FixtureSignalAdapter`, `FixtureCatalog`, fixture data builders |
| **Free API Adapters** | `market_radar/shared/free_api_adapters.py` | Binance adapters, news adapters, `REAL_FREE_API_ADAPTERS` registry, `create_real_free_api_adapter()` |
| **Quality Gate** | `market_radar/shared/gate_contract.py` | `QualityGate`, `SendReadinessGate` |
| **Renderer** | `market_radar/shared/renderer_contract.py` | `CardRenderer` (all 5 card families) |
| **Sender** | `market_radar/shared/sender_contract.py` | `TGTestGroupSender` |
| **Evidence Ledger** | `market_radar/shared/evidence_ledger.py` | `EvidenceLedger`, `create_evidence_ledger()` |
| **Pipeline** | `market_radar/shared/pipeline.py` | `SharedPipeline` (adapter→gate→renderer→sender→ledger) |
| **Noise Gate** | `market_radar/shared/noise_gate.py` | `DeterministicNoiseGate` (Signal Spine's pre-signal gate) |
| **Signal Registry** | `market_radar/shared/signal_registry.py` | `SignalRegistry` (CRUD, dedup, evidence, lifecycle) |
| **Signal Orchestrator** | `market_radar/shared/signal_orchestrator.py` | `SignalOrchestrator` (observation→gate→registry→result) |
| **Event Intelligence** | `market_radar/shared/event_intelligence_semantics.py` | `EventIntelligenceResult`, `IntelligenceDecision`, `evaluate_event_semantics()` |
| **Dry-Run Renderer** | `market_radar/shared/dry_run_renderer.py` | `DryRunRenderer`, `DryRunOutput` |
| **AI Fallback** | `market_radar/shared/ai_fallback.py` | `AIInterpreter`, `generate_template_interpretation()` |

---

## 2. Deprecated or Overlapping Modules

These modules SHOULD NOT be used as sources of truth for Signal Spine. They either duplicate the canonical modules or are legacy artifacts.

| Module | Reason for Deprecation | Replacement |
|--------|----------------------|-------------|
| `scripts/market_radar_card_type_registry_v112a.py` | Standalone script, not importable by shared pipeline | `shared/gate_contract.py` + `shared/models.py` for card type definitions |
| `scripts/market_radar_dedupe_cooldown_gate_v112i.py` | Standalone script, not pipeline-integrated | `shared/noise_gate.py` (`DeterministicNoiseGate`) + `shared/signal_registry.py` |
| `scripts/market_radar_quality_gate_v117.py` | Duplicates `shared/gate_contract.py` | `shared/gate_contract.py:QualityGate` |
| `scripts/market_radar_renderer_contract_v117.py` | Duplicates `shared/renderer_contract.py` | `shared/renderer_contract.py:CardRenderer` |
| `scripts/market_radar_send_readiness_gate_v117.py` | Duplicates `shared/gate_contract.py:SendReadinessGate` | `shared/gate_contract.py:SendReadinessGate` |
| `scripts/market_radar_evidence_ledger_v117.py` | Duplicates `shared/evidence_ledger.py` | `shared/evidence_ledger.py:EvidenceLedger` |
| `scripts/deduplicate_event_candidates.py` | CSV-based dedup for historical pipeline | `shared/noise_gate.py` + `shared/signal_registry.py` |
| `scripts/market_radar_signal_merge.py` | Part of old pipeline | `shared/signal_registry.py:create_signal()` and `_append_observation_to_signal()` |
| `scripts/market_radar_pre_send_gate.py` | Old gate not used in shared pipeline | `shared/gate_contract.py:SendReadinessGate` |
| `scripts/market_radar_same_asset_cooldown_gate_v111f.py` | Old cooldown gate | `shared/noise_gate.py` dedup rules |
| `scripts/market_radar_signal_value_gate_v111b.py` | Old value gate | `shared/gate_contract.py:QualityGate` |
| `scripts/market_radar_signal_trust_gate.py` | Old trust gate | Not replaced — trust is now part of `DataQuality` in Observation |
| `scripts/market_radar_signal_envelope_v112h.py` | Old envelope format | `Observation` model in `shared/models.py` |
| `scripts/market_radar_state_key_validator_v112l.py` | Old state key format | `SignalRegistry` dedup keys |

**Note for integration:** These script files should NOT be deleted during integration (per audit rules). They remain as historical artifacts. The integration branch should simply not import them.

---

## 3. Core Lane (中间执行端) — Allowed Modification Scope

The Core Lane is responsible for Signal Spine models, noise gate, registry, and orchestrator. It operates in `cei_signal_core`.

### MAY MODIFY:
| File | Purpose of Modifications |
|------|------------------------|
| `market_radar/shared/models.py` | **PRIMARY** — Add Observation, Signal, SignalStatus, EvidenceLink, NoiseGateResult, GateVerdict, StatusTransition, ObservationStatus, DataQuality, SignalSpineResult, SIGNAL_SPINE_VERSION |
| `market_radar/shared/noise_gate.py` | Commit existing `DeterministicNoiseGate` from worktree |
| `market_radar/shared/signal_registry.py` | Commit existing `SignalRegistry` from worktree |
| `market_radar/shared/signal_orchestrator.py` | Commit existing `SignalOrchestrator` from worktree |
| `market_radar/shared/ai_fallback.py` | Commit existing `AIInterpreter` from worktree |
| `market_radar/shared/adapter_contract.py` | Add `to_observation()` method to `SignalAdapter` ABC |
| `market_radar/shared/free_api_adapters.py` | Update adapters to support `to_observation()` |
| `market_radar/shared/evidence_ledger.py` | Add `append_to_signal()` and `query_by_signal()` methods |

### MUST NOT MODIFY:
| File | Reason |
|------|--------|
| `market_radar/shared/renderer_contract.py` | IO lane responsibility |
| `market_radar/shared/sender_contract.py` | IO lane responsibility |
| `market_radar/shared/pipeline.py` | Integration responsibility — both lanes merge here |
| `market_radar/shared/gate_contract.py` | Integration responsibility — gates bridge old and new |
| Any file in `scripts/` | Historical artifacts |
| Any file in `tests/` | Both lanes add tests |
| `config/`, `data/`, `fixtures/` | IO lane may add fixtures |

### MAY CREATE:
| File | Purpose |
|------|--------|
| `tests/test_signal_spine_models.py` | Unit tests for new models |
| `tests/test_noise_gate.py` | Unit tests for DeterministicNoiseGate |
| `tests/test_signal_registry.py` | Unit tests for SignalRegistry |
| `tests/test_signal_orchestrator.py` | Unit tests for SignalOrchestrator |

---

## 4. IO Lane (右侧执行端) — Allowed Modification Scope

The IO Lane is responsible for rendering, sending, dry-run, event intelligence semantics, and fixture data. It operates in `cei_signal_io`.

### MAY MODIFY:
| File | Purpose of Modifications |
|------|------------------------|
| `market_radar/shared/renderer_contract.py` | Accept `Signal` in addition to `NormalizedSignal` |
| `market_radar/shared/sender_contract.py` | No changes expected, but may extend for dry-run confirmation |
| `market_radar/shared/dry_run_renderer.py` | Commit existing `DryRunRenderer` from worktree |
| `market_radar/shared/event_intelligence_semantics.py` | Commit existing; may need to adapt to `Signal` model |
| `market_radar/shared/hyperliquid_info_adapter.py` | Commit existing `HyperliquidInfoFreeApiAdapter` |
| `fixtures/` | Commit all fixture files from IO worktree |
| `tests/test_signal_spine_io_v1.py` | Commit existing IO tests |
| `scripts/run_signal_spine_v1_demo.py` | Commit existing demo runner |

### MUST NOT MODIFY:
| File | Reason |
|------|--------|
| `market_radar/shared/models.py` | Core lane adds models first; IO lane imports only |
| `market_radar/shared/noise_gate.py` | Core lane responsibility |
| `market_radar/shared/signal_registry.py` | Core lane responsibility |
| `market_radar/shared/signal_orchestrator.py` | Core lane responsibility |
| `market_radar/shared/gate_contract.py` | Integration responsibility |

### MAY CREATE:
| File | Purpose |
|------|--------|
| `fixtures/*.json` | Already created in IO worktree |
| `tests/test_dry_run_renderer.py` | Additional unit tests |
| `tests/test_event_intelligence_semantics.py` | Tests for 4-category decision system |

---

## 5. Recommended Merge Sequence

The integration into `workbench/overnight-signal-spine-v1` should proceed in this order:

### Phase 1: Foundation (Core Lane)
```
Step 1: Create docs directories (if not exist)
Step 2: Add new models to shared/models.py (Observation, Signal, SignalStatus, etc.)
Step 3: Commit shared/noise_gate.py
Step 4: Commit shared/signal_registry.py
Step 5: Commit shared/signal_orchestrator.py
Step 6: Commit shared/ai_fallback.py
Step 7: Add to_observation() to adapter_contract.py
Step 8: Update free_api_adapters.py for to_observation()
Step 9: Update evidence_ledger.py with query/append methods
Step 10: Core unit tests
```
**Risk of conflicts:** HIGH (models.py is extensively modified)

### Phase 2: Output (IO Lane)
```
Step 11: Commit dry_run_renderer.py
Step 12: Commit event_intelligence_semantics.py
Step 13: Commit hyperliquid_info_adapter.py
Step 14: Commit all fixture files
Step 15: Commit IO tests and demo runner
Step 16: IO unit tests
```
**Risk of conflicts:** LOW (all new files)

### Phase 3: Integration
```
Step 17: Update gate_contract.py to accept Signal
Step 18: Update renderer_contract.py to accept Signal
Step 19: Update pipeline.py:
    - Add SignalOrchestrator-based run path
    - Wire: adapter → to_observation → DeterministicNoiseGate → SignalRegistry → QualityGate → CardRenderer → SendReadinessGate → sender → ledger
    - Add dry-run mode option
Step 20: Integration tests
Step 21: Full e2e verification
```
**Risk of conflicts:** MEDIUM (pipeline.py and gate_contract.py changes)

---

## 6. Files with Predicted Merge Conflicts

| File | Phase | Conflict Type | Resolution Strategy |
|------|-------|---------------|-------------------|
| `market_radar/shared/models.py` | Phase 1 | EXTENSIVE — both lanes add imports and classes | Core lane adds models FIRST; IO lane only imports. Use `git merge` with `--ours` strategy for models.py, then add IO imports manually |
| `market_radar/shared/pipeline.py` | Phase 3 | MODERATE — new `process_observation()` path added | Both lanes keep existing `run()` method; new method is additive |
| `market_radar/shared/gate_contract.py` | Phase 3 | LOW — may need `accept_signal()` overload | Add overloaded method; don't change existing `evaluate()` signature |
| `market_radar/shared/renderer_contract.py` | Phase 2 | LOW — may need `render_signal()` method | Add method; don't change existing `render()` |
| `market_radar/shared/adapter_contract.py` | Phase 1 | LOW — `to_observation()` is additive | Add new method to ABC; existing subclasses get default implementation |
| `market_radar/shared/evidence_ledger.py` | Phase 1 | LOW — new methods are additive | Add methods; don't change existing `record()` API |

---

## 7. Minimum End-to-End Call Path

The minimal working integration should satisfy:

```python
# Minimum viable Signal Spine e2e call path:
from market_radar.shared.models import Observation, Signal, SignalSpineResult
from market_radar.shared.free_api_adapters import MultiAssetMarketSyncFreeApiAdapter
from market_radar.shared.signal_orchestrator import SignalOrchestrator
from market_radar.shared.renderer_contract import CardRenderer
from market_radar.shared.sender_contract import TGTestGroupSender
from market_radar.shared.evidence_ledger import EvidenceLedger

# 1. Adapter → Observation
adapter = MultiAssetMarketSyncFreeApiAdapter()
normalized_signal = adapter.fetch()
observation = adapter.to_observation()  # New method

# 2. Observation → Signal (via orchestrator)
orchestrator = SignalOrchestrator()
result: SignalSpineResult = orchestrator.process(observation)
assert result.gate_passed, "Gate should pass for valid Binance data"
signal = result.signal

# 3. Signal → RenderedCard
renderer = CardRenderer()
# Need: renderer.render_signal(signal) or renderer.render_signal(signal, decision)

# 4. Card → TG test send (optional, dry-run mode)
# sender = TGTestGroupSender()
# tg_result = sender.send(rendered_card, readiness)

# 5. Record evidence
ledger = EvidenceLedger()
ledger.record(...)

print(f"Signal Spine e2e: signal_id={signal.signal_id}, "
      f"status={signal.status.value}, "
      f"assets={signal.affected_assets}")
```

### Verification test (run after integration):
```bash
# Core lane unit tests
python -m pytest tests/test_signal_spine_models.py -v
python -m pytest tests/test_noise_gate.py -v
python -m pytest tests/test_signal_registry.py -v
python -m pytest tests/test_signal_orchestrator.py -v

# IO lane tests
python -m pytest tests/test_signal_spine_io_v1.py -v

# Full e2e (fixture only, no network)
python scripts/run_signal_spine_v1_demo.py --fixture --dry-run

# Full e2e (with real Binance data)
python scripts/run_market_radar_v117_shared_pipeline_real_one_shot.py
```

---

## 8. Final Acceptance Commands

After integration is complete, run these commands to verify correctness:

```bash
# 1. All Spine models import correctly
python -c "from market_radar.shared.models import Observation, Signal, SignalStatus, EvidenceLink, CardFamily, DataSourceType; print('Models OK')"

# 2. Noise gate imports and instantiates
python -c "from market_radar.shared.noise_gate import DeterministicNoiseGate; g = DeterministicNoiseGate(); print('NoiseGate OK')"

# 3. Signal registry creates and persists
python -c "from market_radar.shared.signal_registry import create_signal_registry; r = create_signal_registry(); print('Registry OK')"

# 4. Orchestrator loads
python -c "from market_radar.shared.signal_orchestrator import create_orchestrator; o = create_orchestrator(); print('Orchestrator OK')"

# 5. Event intelligence semantics
python -c "from market_radar.shared.event_intelligence_semantics import evaluate_event_semantics, IntelligenceDecision; print('EI Semantics OK')"

# 6. Dry-run renderer
python -c "from market_radar.shared.dry_run_renderer import create_dry_run_renderer; d = create_dry_run_renderer(); print('DryRun OK')"

# 7. Full pipeline (fixture mode, no network)
python scripts/run_signal_spine_v1_demo.py --fixture --dry-run

# 8. Existing tests still pass
python -m pytest tests/test_cn_number_formatters.py -v
python -m pytest tests/test_position_pnl_consistency.py -v

# 9. Existing pipeline still works
python -c "
from market_radar.shared.pipeline import run_pipeline;
fixture_results, real_results, ledger = run_pipeline(include_fixtures=True, include_real_api=False);
assert len(fixture_results) == 5, f'Expected 5 fixture results, got {len(fixture_results)}';
print(f'Pipeline OK: {len(fixture_results)} fixture results, {len(ledger.entries())} ledger entries')
"

# 10. Verify no trading instructions in any output
python -c "
from market_radar.shared.event_intelligence_semantics import IntelligenceDecision;
assert IntelligenceDecision.OBSERVE.value == '观察';
assert IntelligenceDecision.RISK_TIP.value == '风险提示';
assert IntelligenceDecision.BLOCK.value == '禁止';
assert IntelligenceDecision.DISCARD.value == '丢弃';
print('Event intelligence decisions correctly use observation-only semantics')
"
```

---

## 9. Remaining Architectural Risks

1. **Observation vs NormalizedSignal duality:** The pipeline will temporarily support both `NormalizedSignal` (for backward compat with existing test runners) and `Observation` (for Signal Spine). This duality should be resolved in v2.0 by making all adapters produce `Observation` directly.

2. **Registry storage split:** `SignalRegistry` (JSON) and `EvidenceLedger` (JSONL) have overlapping concerns. Future consolidation should make `EvidenceLedger` a write-through log for `SignalRegistry`.

3. **No true dedup integration:** The `DeterministicNoiseGate` dedup requires the `SignalRegistry` to be loaded before gate evaluation. In a long-running daemon, this means the registry must be in memory.

4. **Missing daemon/loop pattern:** Neither the current pipeline nor Signal Spine supports continuous monitoring. The current code is one-shot only. The `SendReadinessGate` explicitly blocks daemon/loop execution.

5. **Test coverage gap:** Only 2 unit tests exist for the entire codebase. All integration work must add tests.
