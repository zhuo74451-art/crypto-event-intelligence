# Market Radar v1.11-E — Small Batch Dry-run Handoff

**run_id**: 20260604_185143
**task_id**: 20260604_185143.r01
**gate_version**: v1.11-d
**generated_at**: 2026-06-04 18:57 UTC+8
**status**: done

---

## What was done

v1.11-E Small Batch Live-like SignalValueGate Dry-run — 5 scenarios, 20 signals total.

Created and executed `scripts/run_market_radar_signal_value_gate_v111e_small_batch_dryrun.py`
which runs the calibrated v1.11-D SignalValueGate on 5 realistic small-batch (3-5 signal)
scenarios to verify gate behavior at production-like batch sizes.

## Key results

| Metric | v1.11-D (n=15) | v1.11-E (n=20) | Delta |
|--------|---------------|---------------|-------|
| Allow | 86.7% | 70.0% | **-16.7%** |
| Observe | 0.0% | 15.0% | **+15.0%** |
| Block | 13.3% | 15.0% | +1.7% |
| Suspected FP | 2 | N/A (no FP detection in v1.11-E) | — |
| Cooldown issues | 0 | 1 (ARB repeat) | +1 |

## Verdict on the 5 open questions from v1.11-D

1. **SignalValueGate filters low-value signals?** YES. In small batches without
   the mega-batch multi_asset_sync inflation, signals with incomplete field data
   route to observe (15%) instead of allow.

2. **allow/observe/block distribution reasonable?** YES. 70/15/15 is a healthy
   distribution for a gate that should be conservative but not dead. Batch E
   (low-quality day) correctly routes 80% to observe/block.

3. **multi_asset_sync over-fires in small batches?** NO. The v1.11-D calibration
   (requiring OI/vol backing) prevents over-fire. Multi's main effect now is
   amplifying score for already-confirmed signals, not pushing weak signals to allow.

4. **Cooldown needed?** YES. Batch D proves same-asset repeats pass the gate
   independently. Cooldown must be a separate layer (pre_send_gate or cooldown module).

5. **Ready for pre_send_gate?** NOT YET. One blocker: cooldown not implemented.
   Gate logic itself is sound. Recommend: v1.11-F implement cooldown →
   v1.11-G wire pre_send_gate.

## Files created/modified

### New files
- `scripts/run_market_radar_signal_value_gate_v111e_small_batch_dryrun.py` — main dry-run script
- `results/market_radar_v111e_small_batch_dryrun_result.json` — full results
- `runs/market_radar/v111e_small_batch_dryrun.md` — detailed report
- `runs/market_radar/v111e_small_batch_dryrun_handoff.md` — this file

### Existing files (unchanged)
- `scripts/market_radar_signal_value_gate_v111b.py` — gate implementation (NOT modified)
- `scripts/test_market_radar_signal_value_gate_v111b.py` — tests (NOT modified)

## Test results

Existing tests remain at 109/109 passed (verified below, no regressions).

## Next recommended step

**v1.11-F**: Implement same-asset cooldown as a separate module (not inside SignalValueGate).
- Input: list of gate results + timestamps
- Logic: first occurrence per asset passes; subsequent within cooldown window
  (e.g. 10-30 min) suppressed unless value_score increases significantly
- Output: `cooldown_passed` boolean + `cooldown_reason` string
- This should be the layer BETWEEN SignalValueGate and pre_send_gate.

Only after v1.11-F completes should v1.11-G wire pre_send_gate.

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
