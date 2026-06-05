# Market Radar v1.11-F — Same-Asset Cooldown Gate Dry-run Report

**run_id**: 20260604_185143
**task_id**: 20260604_185143.r02
**gate_version**: v1.11-f
**generated_at**: 2026-06-04 19:11 UTC+8
**status**: done

---

## What v1.11-F Does

Implements an independent **Same-Asset Cooldown Gate** as a separate layer between
SignalValueGate and pre_send_gate.

- **SignalValueGate** answers: "Is this signal valuable enough?"
- **CooldownGate** answers: "Should we send it NOW, or did we just send for this asset?"

This is the only remaining blocker for pre_send_gate integration, as identified in v1.11-E.

## Cooldown Rules

| Rule | Behavior |
|------|----------|
| First occurrence | Always allow (start cooldown timer) |
| Same asset within 10 min, similar score | **cooldown_suppress** — do not send |
| Same asset within 10 min, score improves by >= 15 pts | **upgrade_override** — allow as upgrade card |
| Same asset after 10 min window expires | **allow** — reset cooldown window |
| Different assets | Tracked independently — no cross-asset suppression |
| Signal blocked by value gate | Skip cooldown check entirely |
| No value gate result available | Conservative: allow (don't silently drop) |

## Dry-run Results (5 scenarios, 18 signals)

| Batch | Scenario | Signals | Allow | Suppress | Upgrade | Repeated |
|-------|----------|---------|-------|----------|---------|----------|
| F1 | Same-Asset Repeat | 3 | 1 | 2 | 0 | ARB |
| F2 | Upgrade Override | 2 | 1 | 0 | 1 | ETH |
| F3 | Window Expiry | 2 | 2 | 0 | 0 | SOL |
| F4 | Multi-Asset Interleaving | 5 | 3 | 2 | 0 | BTC, ETH |
| F5 | Mixed Integration | 6 | 4 | 1 | 1 | SUI |
| **Total** | | **18** | **11 (61.1%)** | **5 (27.8%)** | **2 (11.1%)** | **5 assets** |

### Aggregate Cooldown Metrics

| Metric | Count | Rate |
|--------|-------|------|
| cooldown_allow_count | 11 | 61.1% |
| cooldown_suppress_count | 5 | 27.8% |
| upgrade_override_count | 2 | 11.1% |
| repeated_assets | 5 | ARB, BTC, ETH, SOL, SUI |

### Value Gate Reference (same signals)

| Decision | Count |
|----------|-------|
| value_allow | 15 |
| value_observe | 2 |
| value_block | 1 |

### Key Finding: Without cooldown, 5 extra sends would have occurred

All 5 `cooldown_suppress` signals passed SignalValueGate as `allow`. Without the
cooldown layer, they would have been sent to the test channel — flooding it with
same-asset repeats within minutes.

## Batch-by-Batch Analysis

### F1: Same-Asset Repeat — Cooldown Suppression

ARB appears 3 times at T+0, T+4, T+8 min:
- T+0: allow (first occurrence, score=100)
- T+4: cooldown_suppress (4 min within 10 min window, same score)
- T+8: cooldown_suppress (8 min within 10 min window, same score)

**Verified**: Same-asset repeats are correctly suppressed within the cooldown window.

### F2: Upgrade Override — Score Improvement

ETH appears twice: T+0 (weak, score=10) and T+5 (strong, score=115):
- T+0: observe (SignalValueGate: price only, no confirmations — score=10). Cooldown: allow (first occurrence)
- T+5: allow (SignalValueGate: price+OI+volume+funding — score=115). Cooldown: **upgrade_override** (Δ+105 >> 15)

**Verified**: When value_score improves significantly, the cooldown gate issues an
upgrade_override rather than silently suppressing an important escalation.

### F3: Window Expiry — Allow After Cooldown

SOL at T+0 and T+12:
- T+0: allow (first occurrence, score=75)
- T+12: allow (12 min > 10 min window, score=75)

**Verified**: After the cooldown window expires, the same asset can be sent again
as a normal allow (not upgrade_override, because it's a clean reset).

### F4: Multi-Asset Interleaving

BTC, ETH, BTC, ETH, SOL at T+0, +3, +5, +7, +9:
- T+0 BTC: allow (first)
- T+3 ETH: allow (first, independent)
- T+5 BTC: cooldown_suppress (5 min since BTC first)
- T+7 ETH: cooldown_suppress (4 min since ETH first)
- T+9 SOL: allow (first, independent)

**Verified**: Per-asset cooldown tracking works correctly. BTC and ETH are suppressed
independently. SOL passes because it's a different asset.

### F5: Mixed Integration — Full Pipeline

SUI, ETH, DOT, SUI, LINK, SUI at T+0, +2, +4, +6, +8, +10:
- T+0 SUI: value=allow, cooldown=allow → SEND
- T+2 ETH: value=allow, cooldown=allow → SEND
- T+4 DOT: value=block, cooldown=allow → BLOCKED (value gate) — not a cooldown concern
- T+6 SUI: value=allow, cooldown=cooldown_suppress → COOLDOWN SUPPRESS
- T+8 LINK: value=observe, cooldown=allow → OBSERVE (not sent) — observe + first occurrence
- T+10 SUI: value=allow (score=140), cooldown=upgrade_override → SEND (upgrade)

**Verified**: Full pipeline integration. SignalValueGate blocks/observes first, then
CooldownGate applies rate limiting on the allowed signals. The pipeline layers
correctly: value gate → cooldown gate → send decision.

## Pre-Send Gate Readiness Assessment

| Check | Status |
|-------|--------|
| Cooldown gate suppresses same-asset repeats | PASS |
| Upgrade override works for signal escalation | PASS |
| Per-asset independent tracking | PASS |
| Separation of concerns maintained (value vs rate-limit) | PASS |
| Integration with SignalValueGate verified | PASS |

**Verdict: READY** for v1.11-G pre_send_gate integration dry-run.

No blockers remain. The cooldown gate can now be wired between SignalValueGate and
pre_send_gate in a dry-run pipeline. Do NOT send to TG yet.

## Test Results

| Test Suite | Passed | Total |
|------------|--------|-------|
| Cooldown gate (new) | 18 | 18 |
| SignalValueGate (v1.11-D) | 24 | 24 |
| Pre-send gate (v1.10-G) | 16 | 16 |
| Signal trust gate (v1.10-C) | 26 | 26 |
| Sender gate coverage (v1.10-H) | 15 | 15 |
| Card router (v1.10-A) | 28 | 28 |
| **Total** | **127** | **127** |

## Files Created

- `scripts/market_radar_same_asset_cooldown_gate_v111f.py` — Cooldown gate module (CooldownState class + evaluate_cooldown function)
- `scripts/test_market_radar_same_asset_cooldown_gate_v111f.py` — 18 unit tests
- `scripts/run_market_radar_same_asset_cooldown_v111f_dryrun.py` — 5-scenario dry-run
- `results/market_radar_v111f_same_asset_cooldown_result.json` — Full dry-run results
- `runs/market_radar/v111f_same_asset_cooldown.md` — This report
- `runs/market_radar/v111f_same_asset_cooldown_handoff.md` — Handoff summary

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
