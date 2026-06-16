# Signal Spine IO v1 — Data Edge & Independent Verification

## Overview

This lane provides the "Data Edge" layer for the signal-spine-v1 pipeline: external
input handling, fixture fallback, dry-run output, and independent verification assets.

All components are designed to slot into the future core Spine/Registry without
modifying existing core contracts.

## File Ownership

### Modified Files (existing contracts extended)
None — all additions are new files that complement existing structures.

### New Files

| File | Purpose |
|------|---------|
| `market_radar/shared/hyperliquid_info_adapter.py` | Hyperliquid Info API read-only adapter |
| `market_radar/shared/event_intelligence_semantics.py` | Event Intelligence decision semantics |
| `market_radar/shared/dry_run_renderer.py` | Dry-run output renderer (JSON/MD/TG card) |
| `fixtures/event_high_quality.json` | High-quality market event fixture |
| `fixtures/event_duplicate.json` | Duplicate event fixture (same dedup_key) |
| `fixtures/event_old_news_rehash.json` | Old news rehash fixture |
| `fixtures/event_no_asset.json` | No-clear-asset event fixture |
| `fixtures/event_insufficient_source.json` | Insufficient source fixture |
| `fixtures/event_pump_risk.json` | High pump/FOMO risk fixture |
| `fixtures/event_missing_fields.json` | Missing data fields fixture |
| `fixtures/real_binance_response_sample.json` | Sample Binance API response |
| `fixtures/golden_multi_asset_market_sync.json` | Golden reference output |
| `fixtures/loader.py` | Fixture loading utility |
| `fixtures/README.md` | Fixture documentation |
| `scripts/run_signal_spine_v1_demo.py` | Demo / verification runner |
| `tests/test_signal_spine_io_v1.py` | Independent verification tests |
| `docs/signal_spine_io_v1_verification.md` | This document |

## Required Core Interfaces

When the core Spine/Registry is implemented in the integration branch, the
following interfaces are needed to fully connect these edge components:

| Edge Component | Core Interface Needed | Notes |
|----------------|----------------------|-------|
| `HyperliquidInfoFreeApiAdapter` | `SignalAdapter` registration in `REAL_FREE_API_ADAPTERS` | Currently standalone — does NOT extend SignalAdapter to avoid modifying existing contract |
| `DryRunRenderer` | Pipeline integration: QualityGate → EventIntelligence → Renderer | Currently standalone — call render() after gate decision |
| `EventIntelligenceResult` | Decision stage in pipeline | Core should call `evaluate_event_semantics()` after QualityGate |
| `fixtures/` | Fixture loading in Registry | Currently standalone via `loader.py` |
| `scripts/run_signal_spine_v1_demo.py` | Registry's pipeline runner | Current demo self-contains all logic |

### Hyperliquid Info API — Bridge to `REAL_FREE_API_ADAPTERS`

The Hyperliquid adapter is currently standalone (not registered in
`REAL_FREE_API_ADAPTERS`). When the core pipeline is ready, add:

```python
from market_radar.shared.hyperliquid_info_adapter import HyperliquidInfoFreeApiAdapter
from market_radar.shared.free_api_adapters import REAL_FREE_API_ADAPTERS

# Register alongside existing Binance adapters
REAL_FREE_API_ADAPTERS["hyperliquid_market_sync"] = HyperliquidInfoFreeApiAdapter
```

### Event Intelligence — Bridge to Pipeline Decision Stage

The event intelligence semantics should be called after QualityGate evaluation:

```python
from market_radar.shared.event_intelligence_semantics import evaluate_event_semantics

# After QualityGate decision:
ei_result = evaluate_event_semantics(signal_data, is_duplicate=check_dedup(signal))
renderer.render(signal, ei_result)
```

### Dry-Run Renderer — Bridge to Pipeline Output

```python
from market_radar.shared.dry_run_renderer import DryRunRenderer

# In pipeline's output stage:
if dry_run_mode:
    renderer = DryRunRenderer(output_dir="./results/dry_run")
    output = renderer.render(fixture_data, signal=normalized_signal)
    output.save_json(output_dir)
    output.save_markdown(output_dir)
```

## Usage

```bash
# Full fixture verification (offline-safe)
python scripts/run_signal_spine_v1_demo.py --fixture --dry-run

# With optional network test
python scripts/run_signal_spine_v1_demo.py --fixture --dry-run --network

# Quick load/safety check only
python scripts/run_signal_spine_v1_demo.py --verify

# Python tests (offline-safe, no API keys)
python -m pytest tests/test_signal_spine_io_v1.py -v
```

## Merge Conflict Risk Assessment

| Area | Risk | Mitigation |
|------|------|------------|
| New files (this lane) | Low — no overlap with existing code | All new files, no modifications |
| `free_api_adapters.py` | Low — not modified | If integration branch adds Hyperliquid adapter here, ours may need dedup |
| `adapter_contract.py` | Low — not modified | If integration branch changes contract signature, `hyperliquid_info_adapter.py` may need update |
| `dry_run_renderer.py` | Low — depends on stable models.py | Models.py should not change structurally |

## Remaining IO Gaps

1. **More free API sources**: Only Binance and Hyperliquid covered. CoinGecko free API
   could be added but requires rate limiting.
2. **Full Hyperliquid adapter**: Current adapter only fetches `allMids`. `meta` endpoint
   for universe tracking could be added.
3. **Production integration**: Core Spine/Registry must wire these edge components
   into the pipeline.

## Safety Guarantees

- ❌ No real Telegram send
- ❌ No API keys in fixtures
- ❌ No trading instructions (buy/sell/long/short)
- ❌ No automatic publishing
- ❌ No automatic trading
- ✅ All outputs clearly marked as dry-run
- ✅ Production Send = False always
- ✅ Network-optional tests
- ✅ Dedup prevents duplicate processing
