# Market Radar v1.11-G — Full Gate Pipeline Dry-run Handoff

**run_id**: 20260604_193108
**task_id**: 20260604_193108.r01
**status**: done
**result_source**: claude_code_executor
**completed_at**: 2026-06-04 19:40 UTC+8

---

## What was done

Executed v1.11-G: chained SignalValueGate → CooldownGate → pre_send_gate into a complete three-layer dry-run pipeline.

### New files created
- `scripts/run_market_radar_v111g_full_gate_pipeline_dryrun.py` — Pipeline orchestration script (6 scenarios, 26 signals)
- `results/market_radar_v111g_full_gate_pipeline_dryrun_result.json` — Full pipeline output (aggregate + per-signal detail)
- `runs/market_radar/v111g_full_gate_pipeline_dryrun.md` — Comprehensive report with decision matrix
- `runs/market_radar/v111g_full_gate_pipeline_dryrun_handoff.md` — This file

### What the pipeline does
1. **SignalValueGate** (v1.11-d): Multi-factor value evaluation — allow / observe / block based on price movement, OI, volume, funding, multi-asset sync
2. **CooldownGate** (v1.11-f): Same-asset rate limiting — 10-min window, upgrade_override at Δ>=15
3. **pre_send_gate** (v1.10-G): Safety check — source trust, TTL expiry, payload validation

### Aggregate results (26 signals, 6 scenarios)
| Outcome | Count | Rate |
|---------|-------|------|
| send_candidate | 12 | 46.2% |
| send_candidate_upgrade | 2 | 7.7% |
| blocked_by_value_gate | 4 | 15.4% |
| suppressed_by_cooldown | 3 | 11.5% |
| blocked_by_pre_send_gate | 5 | 19.2% |
| observe | 2 | 7.7% |

### Test regression check
127/127 passed, 0 failed, 0 regressions (SignalValueGate 24/24, CooldownGate 18/18, pre_send_gate 16/16, SignalTrustGate 26/26, Sender Coverage 15/15, Card Router 28/28)

### Expectation verification
0 mismatches across all 26 signals — all pipeline outcomes match expected results.

## Key decisions made

1. **Pre-send gate runs on observe signals too.** The pipeline checks pre_send_gate for both "allow" and "observe" signals (when cooldown allows). This provides full observability — we know whether an observed signal would also have been safety-blocked. The `observe__pre_send_blocked` status captures this edge case.

2. **Mock payloads for dry-run.** Since we cannot use the real card renderer (no secrets, no TG), the pipeline constructs minimal valid payloads (`text` + `parse_mode`) for pre_send_gate validation. Invalid payload variants (empty text, missing parse_mode) are used to test pre_send blocking.

3. **Per-scenario timestamp management.** Each scenario uses `_recent_ts()` for valid signals and `_stale_ts()` (2h old) to test TTL expiry. This avoids real-clock dependency while still exercising the TTL check.

4. **Expectation tracking.** Each signal carries an `expect_final` field. The pipeline reports mismatches between expected and actual outcomes — providing self-validation.

## What was NOT done (by design)

- No TG send (test or formal channel)
- No secrets loaded or printed
- No paid APIs
- No loop/daemon/cron
- No files deleted
- No pre_send_gate bypass — all three layers are exercised
- No formal channel unfreeze

## Pre-send gate readiness assessment

**Ready for test-channel dry-run with real card rendering** — NOT ready for TG delivery.

Conditions met:
- [x] Cooldown suppresses same-asset repeats
- [x] Pre-send gate catches unsafe signals (source trust, TTL, payload)
- [x] Pipeline correctly identifies send_candidate signals
- [x] Observe layer captures low-confidence signals

Remaining blockers before real TG send:
- [ ] Card router/renderer integration (mock payloads → real rendered cards)
- [ ] Actual TG send function wiring (currently completely dry)
- [ ] Production config and secrets management

## Recommended next step (v1.11-H)

Run a **test-channel live dry-run**: signals through full pipeline → mock cards rendered → cards logged but NOT sent. This validates end-to-end with real payload rendering before any TG delivery.

Do NOT unfreeze formal channel. Do NOT send to TG yet. Continue test-channel-only validation.

## Security

- [x] No TG send
- [x] No formal channel
- [x] No secrets loaded
- [x] No paid APIs
- [x] No loop/daemon/cron
- [x] No files deleted
- [x] All code in `C:\Users\PC\Desktop\Projects\事件情报系统`
