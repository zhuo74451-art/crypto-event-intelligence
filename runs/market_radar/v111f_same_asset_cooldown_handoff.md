# Market Radar v1.11-F — Same-Asset Cooldown Gate Handoff

**run_id**: 20260604_185143
**task_id**: 20260604_185143.r02
**gate_version**: v1.11-f
**generated_at**: 2026-06-04 19:11 UTC+8
**status**: done

---

## What was done

v1.11-F Same-Asset Cooldown Gate — implemented independent cooldown layer between
SignalValueGate and pre_send_gate. This is the sole remaining blocker identified in
v1.11-E for pre_send_gate integration.

Created 3 files + 2 docs + 1 result:
- Cooldown gate module: `CooldownState` class + `evaluate_cooldown()` function
- 18 unit tests covering all cooldown states and edge cases
- 5-scenario dry-run proving cooldown works in realistic small-batch conditions

## Key results

| Metric | Value |
|--------|-------|
| cooldown_allow_count | 11 (61.1%) |
| cooldown_suppress_count | 5 (27.8%) |
| upgrade_override_count | 2 (11.1%) |
| repeated_assets | 5 (ARB, BTC, ETH, SOL, SUI) |

### Without cooldown, 5 extra sends would have reached the test channel

All 5 `cooldown_suppress` signals passed SignalValueGate as `allow`. The cooldown
gate correctly prevented them from being sent as same-asset repeats within the
10-minute window.

### Upgrade override prevents over-suppression

2 upgrade_overrides triggered (ETH Δ+105, SUI Δ+40) — when the value_score
improves significantly (>= 15 pts), the cooldown gate allows the repeat as an
"upgrade card" rather than silently suppressing important escalations.

## Verdict on the 5 blocking questions from v1.11-E

1. **SignalValueGate filters low-value signals?** Already confirmed in v1.11-E.
2. **allow/observe/block distribution reasonable?** Already confirmed in v1.11-E.
3. **multi_asset_sync over-fires in small batches?** Already confirmed NOT in v1.11-E.
4. **Cooldown needed?** **YES — NOW IMPLEMENTED.** v1.11-F proves same-asset repeats
   are correctly suppressed within a 10-min window. The `cooldown_suppress_count=5`
   confirms these would have been noise without cooldown.
5. **Ready for pre_send_gate?** **YES.** 0 blockers remain. v1.11-F has resolved the
   only blocker from v1.11-E. Recommend v1.11-G: wire CooldownGate between
   SignalValueGate and pre_send_gate in a dry-run pipeline.

## Cooldown Gate Design

```
SignalValueGate (v1.11-D)     → "Is this signal valuable?"     → allow/observe/block
        |
        v
CooldownGate (v1.11-F)        → "Should we send it NOW?"        → allow/cooldown_suppress/upgrade_override
        |
        v
pre_send_gate (v1.10-G/H)     → "Is it safe to send?"           → allowed/blocked
        |
        v
TG Sender                      → actually sends
```

Key design decisions:
- Separate concern: value judgment vs rate limiting
- Configurable: cooldown_window_minutes=10, upgrade_override_score_delta=15
- Stateful but in-memory: CooldownState tracks per-asset last_allowed_at, value_score, occurrence_count, suppression_count
- Conservative fallback: if no value gate result available, allow (don't silently drop)
- Blocked signals skip cooldown entirely

## Files created/modified

### New files
- `scripts/market_radar_same_asset_cooldown_gate_v111f.py` — Cooldown gate module
- `scripts/test_market_radar_same_asset_cooldown_gate_v111f.py` — 18 unit tests
- `scripts/run_market_radar_same_asset_cooldown_v111f_dryrun.py` — Dry-run with 5 scenarios
- `results/market_radar_v111f_same_asset_cooldown_result.json` — Full dry-run results
- `runs/market_radar/v111f_same_asset_cooldown.md` — Detailed report
- `runs/market_radar/v111f_same_asset_cooldown_handoff.md` — This file

### Existing files (unchanged)
- `scripts/market_radar_signal_value_gate_v111b.py` — NOT modified
- `scripts/test_market_radar_signal_value_gate_v111b.py` — NOT modified
- `scripts/market_radar_pre_send_gate.py` — NOT modified

## Test results

All existing tests re-run: 109/109 passed. New cooldown tests: 18/18 passed.
**Total: 127/127 passed, no regressions.**

| Suite | Passed |
|-------|--------|
| Cooldown gate (new) | 18/18 |
| SignalValueGate | 24/24 |
| Pre-send gate | 16/16 |
| Signal trust gate | 26/26 |
| Sender gate coverage | 15/15 |
| Card router | 28/28 |

## Next recommended step

**v1.11-G**: Wire CooldownGate between SignalValueGate and pre_send_gate in a
dry-run pipeline. Do NOT send to TG. Verify that the full pipeline (value →
cooldown → safety) produces the correct send/suppress/observe/block distribution
before any TG test-channel send.

## Security

| Check | Status |
|-------|--------|
| TG send | NONE |
| Formal channel touched | NONE |
| Secrets loaded | NONE |
| Token/chat_id/key read/printed/saved | NONE |
| Paid API calls | NONE |
| Loop/daemon/cron started | NONE |
| Files deleted | NONE |
| Pre_send_gate connected | NONE |
