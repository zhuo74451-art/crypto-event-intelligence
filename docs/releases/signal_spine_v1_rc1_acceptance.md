> ⚠ **Historical document.** This report reflects the project at commit `9c28c93` (signal-spine-v1-rc1).
> Some conclusions and descriptions (e.g., "price module not connected", "Observation/Signal
> do not exist" if present) have been superseded by subsequent implementations.
> For current status refer to `README.md`, `docs/PROJECT_OVERVIEW.md`, and the
> Week 1 release evidence.

# Signal Spine v1 RC1 — Acceptance Document

## 唯一入口 (Single Entry Point)

```python
from market_radar.shared.pipeline import SharedPipeline

pipeline = SharedPipeline()
spine_result, dry_run_output = pipeline.run_signal_spine(
    adapter=adapter,
    source_label="my_source",
    dry_run=True,
)
```

`SharedPipeline.run()` (old path) preserved unchanged for backward compatibility.

## 数据对象流 (Data Object Flow)

```
SignalAdapter.fetch()
    → NormalizedSignal
    → Observation.from_normalized_signal()
        → observation_fingerprint (source-specific)
        → event_dedup_key (source-agnostic, with time bucket)
    → DeterministicNoiseGate.evaluate_and_aggregate()
        → 10 rule results (NoiseGateResult[])
    → SignalOrchestrator.process()
        → SignalRegistry.create_signal() or merge_observation()
    → EventIntelligenceMapper.populate_result()
        → SignalSpineResult (with emit_card, observation_decision, data_origin)
        → EventIntelligenceResult (OBSERVE/RISK_TIP/BLOCK/DISCARD)
    → DryRunRenderer.render()
        → DryRunOutput (JSON + Markdown + Telegram-style card)
```

## 决策映射 (Decision Mapping)

| Gate/Rules | Final Decision | emit_card | Note |
|---|---|---|---|
| duplicate merged | suppress_duplicate | False | Evidence preserved, no second card |
| high_chase_or_pump_risk + REJECT | BLOCK (禁止) | False | **P0: pump → BLOCK, not DISCARD** |
| stale_or_recycled + REJECT | DISCARD (丢弃) | False | |
| insufficient_source_quality + REJECT | DISCARD (丢弃) | False | |
| single_unverified_source + REJECT | DISCARD (丢弃) | False | |
| passed + any downgrade | RISK_TIP (风险提示) | True | |
| passed + all accept | OBSERVE (观察) | True | |

## 去重语义 (Dedup Semantics)

- **observation_fingerprint**: `sha256(source + title + sorted_assets)` — source-specific
- **event_dedup_key**: `sha256(normalized_title + normalized_assets + event_type + time_bucket)` — source-agnostic
- **Time bucket**: `YYYY-MM-DDTHH` (24h default). Prevents same-title-different-day from merging.
- **Merge**: Same event_dedup_key = append observation + evidence to existing signal. No second card.
- **Different event_type + same title** = NOT merged.

## Fixture / Real / Degraded 区分

| Source Provenance | DataOrigin | Condition |
|---|---|---|
| Real API success | `DataOrigin.REAL` | `source_type` is API/SOURCE and `api_success != False` |
| Fixture mode | `DataOrigin.FIXTURE` | Source type is FIXTURE |
| Network failure | `DataOrigin.DEGRADED` | `api_success == False` or degraded fallback |

`DataOrigin` defined once in `market_radar/shared/models.py`. No duplicate enums.

## 测试证据 (Test Evidence)

```
126 tests passed (115 existing + 11 new RC tests)
  - pump reject → BLOCK (assert "禁止")
  - fixture origin propagation
  - degraded origin propagation
  - canonical DataOrigin (same class from models.py)
  - watch windows only 1h/4h/24h
  - same event, same bucket → merge
  - same title, different day → NOT merge
  - same title, different event_type → NOT merge
  - duplicate → emit_card=False
```

## Fresh Clone 证据

```
Directory: cei_signal_fresh_verify
Branch:    origin/workbench/overnight-signal-spine-v1
Clone:     from remote, no local files copied
API keys:  NOT set
Tests:     126 passed, 0 failed
Demo:      python scripts/run_signal_spine_integration_demo.py --fixture --dry-run
             → All scenarios passed
Git status: clean (no generated files)
```

## 尚未接入 (Not Yet Connected)

- Price backfill commit — waiting for corrected version
- Real Telegram send (blocked by SendReadinessGate as designed)
- Hyperliquid/Binance real network adapters (no API key required, but network-dependent)
- Notion integration
- Continuous daemon/cron execution

## 不允许合并 main 的剩余条件

1. Price backfill commit has not been reviewed — do NOT cherry-pick or merge until corrected version is available
2. Real network integration (Hyperliquid/Binance) is separately gated
3. This branch is for RC review only — not for production deployment
