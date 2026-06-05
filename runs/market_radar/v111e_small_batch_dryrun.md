# Market Radar v1.11-E — Small Batch Live-like SignalValueGate Dry-run

**Generated**: 2026-06-04 18:57 UTC+8
**Gate version**: v1.11-d (calibrated)
**Run version**: v1.11-E

---

## 1. Objective

v1.11-D calibration replay used a single 15-signal mega-batch and found:
- allow=13/15 (87%), observe=0/15 (0%), block=2/15 (13%)
- The large batch inflated multi_asset_sync (8-9 real same-direction assets)
- Executor concluded: "此 allow 率可能是样本中真实信号质量高导致，不一定是 gate 缺陷"

v1.11-E tests the SAME gate logic but in realistic small batches (3–5 signals),
closer to what actual production monitoring would produce.

## 2. Methodology

5 distinct small-batch scenarios, each with a specific test objective:

| Batch | Name | Size | Objective |
|-------|------|------|-----------|
| A | Baseline — Well-Confirmed | 3 | Verify triple-confirmation signals pass. Multi at threshold (3). |
| B | Mixed Confirmation — Observe Test | 3 | Test observe when fields incomplete. 2 real same-dir (multi may not fire). |
| C | Multi-Asset Boundary + Fixture | 4 | Test multi at threshold + fixture exclusion from direction count. |
| D | Same-Asset Repeat — Cooldown | 5 | Demonstrate cooldown gap: ARB appears twice, gate allows both. |
| E | Observe-Dominant — Low Quality | 5 | Test gate's ability to suppress noise: mostly observe/block. |

All 20 signals run through `evaluate_signal_value()` from `market_radar_signal_value_gate_v111b.py` (v1.11-D calibrated gate). No TG send, no secrets, no paid APIs.

## 3. Results

### 3.1 Aggregate Distribution

| Metric | v1.11-D (15 signals) | v1.11-E (20 signals) | Delta |
|--------|---------------------|---------------------|-------|
| Allow | 13 (86.7%) | 14 (70.0%) | **-16.7%** |
| Observe | 0 (0.0%) | 3 (15.0%) | **+15.0%** |
| Block | 2 (13.3%) | 3 (15.0%) | +1.7% |

### 3.2 Per-Batch Breakdown

#### Batch A: Baseline — Well-Confirmed Signals (3 signals)
```
[ALLOW] BTC   score=100  price+OI+vol+multi  (triple confirmation)
[ALLOW] SOL   score=100  price+OI+vol+multi  (triple confirmation)
[ALLOW] ARB   score=100  price+OI+vol+multi  (triple confirmation)
```
**Result**: 3/3 allow. Multi_asset_sync fires at threshold (3 real down).
**Assessment**: Expected baseline — well-confirmed signals correctly pass.

#### Batch B: Mixed Confirmation — Observe Layer Test (3 signals)
```
[ALLOW]   SUI   score=100  price+OI+vol+multi  (triple confirmation)
[OBSERVE] ETH   score= 20  price only           (strong price, no fields)
[BLOCK]   DOT   score= 50  OI only              (price not hit)
```
**Result**: 1 allow, 1 observe, 1 block. Observe layer FIRES.
**Assessment**: 
- ETH: strong price (-7.5%) but OI/vol/funding all missing → gate correctly routes to observe
- DOT: price -4.5% (below 5% threshold), OI present but price not hit → gate correctly blocks
- Multi fires (3 real down) but doesn't save ETH (no OI/vol backing for multi)

#### Batch C: Multi-Asset Boundary + Fixture Exclusion (4 signals)
```
[ALLOW] SOL   score=100  price+OI+vol+multi  (triple confirmation)
[ALLOW] SUI   score= 70  price+OI+multi      (OI confirmed, vol missing)
[ALLOW] ARB   score= 70  price+OI+multi      (OI confirmed, vol missing)
[ALLOW] HYPE  score=120  price+OI+vol+multi  (fixture, triple confirm)
```
**Result**: 4/4 allow.
**Assessment**: 
- SUI and ARB: score=70 (down from 100 due to missing volume -10 penalty). Still allow because OI confirmation counts as strong confirmation.
- HYPE (fixture): opposite direction (up). Multi fires for down direction via 3 real assets. HYPE evaluated independently — passes on its own triple confirmation.
- Fixture correctly excluded from down-direction multi count.

#### Batch D: Same-Asset Repeat — Cooldown Gap Demonstration (5 signals)
```
[ALLOW] ARB   score=100  price+OI+vol+multi  (1st occurrence, T+0)
[ALLOW] ARB   score=100  price+OI+vol+multi  (2nd occurrence, T+10min)
[ALLOW] BTC   score=100  price+OI+vol+multi  (context)
[ALLOW] SUI   score=100  price+OI+vol+multi  (context)
[ALLOW] SOL   score=100  price+OI+vol+multi  (context)
```
**Result**: 5/5 allow. **[COOLDOWN] ARB x2 — gate allows both**.
**Assessment**:
- SignalValueGate evaluates each signal independently — correctly by design.
- ARB appears twice within 10 minutes, both pass with identical scores.
- This CONFIRMS: cooldown must be a separate layer. The gate cannot and should not track temporal proximity.
- Without cooldown, same-asset repeats would flood the test channel.

#### Batch E: Observe-Dominant — Low-Quality Signal Day (5 signals)
```
[OBSERVE] ETH   score= 20  price only            (strong -7.8%, no fields)
[OBSERVE] LTC   score= 20  price only            (-5.5%, no fields)
[ALLOW]   AVAX  score= 65  price+vol+multi       (vol confirmed)
[BLOCK]   DOT   score= 50  OI only               (price -3.2%, below threshold)
[BLOCK]   LINK  score= 10  none                  (-4.0%, no confirmations)
```
**Result**: 1 allow, 2 observe, 2 block.
**Assessment**:
- Gate successfully suppresses low-quality noise: 4/5 signals are NOT allowed.
- ETH and LTC: both have price movement but zero confirmation fields → observe (correct)
- AVAX: price + volume confirmation → allow (correct, has strong confirmation)
- DOT and LINK: price below 5% threshold → block (correct)

### 3.3 Multi-Asset Sync Analysis

| Finding | Detail |
|---------|--------|
| Batches where multi fired | 5/5 (100%) |
| Batches where multi would NOT fire with ≤2 real same-dir | 0/5 (all scenarios had ≥3 real down) |
| Multi contribution to over-allow | LOW in all batches — multi requires OI/vol backing post v1.11-D |
| Key insight | All test scenarios happened to have ≥3 same-direction assets. Real production batches with only 1-2 correlated assets would see multi NOT fire, further reducing allow rate. |

### 3.4 Cooldown Analysis

| Finding | Detail |
|---------|--------|
| Same-asset repeats detected | 1 (ARB in Batch D) |
| Gate behavior | Both occurrences allowed (no cooldown in gate) |
| Risk without cooldown | Same asset flooding test channel with near-identical cards |
| Recommendation | Implement in pre_send_gate or dedicated cooldown module: first occurrence passes, subsequent within 10-30 min suppressed unless value_score increases significantly |

## 4. Key Findings

1. **Allow rate drops 16.7% in small batches**: 70.0% vs 86.7% in v1.11-D. The large batch inflated multi_asset_sync and suppressed observe.

2. **Observe layer activates**: 15.0% observe rate (vs 0% in v1.11-D). Signals with price but incomplete field data now correctly route to observe instead of being pushed to allow by multi_asset_sync.

3. **Multi_asset_sync is not the problem in small batches**: Even when multi fires (≥3 real same-direction), the v1.11-D calibration prevents it from being a "free pass" — it requires OI or volume backing.

4. **Cooldown gap confirmed**: Same-asset repeats pass the gate independently. This is correct gate behavior but confirms cooldown must be a separate layer before pre_send_gate.

5. **Gate discriminates well**: In Batch E (low-quality signal day), 4/5 signals are NOT allowed — proving the gate can filter noise when field data is poor.

## 5. Pre-Send Gate Readiness Assessment

**Status: NOT READY**

**Blockers**:
- [ ] Cooldown not implemented — same-asset repeats would flood test channel

**Conditions met**:
- [x] Observe layer fires correctly in small batches
- [x] Gate is discriminating enough to be useful as a pre-filter
- [ ] Complete v1.11-E validation with real-time data before deciding

**Verdict**: The gate logic is sound. The ONE remaining blocker before pre_send_gate is cooldown. Recommend v1.11-F: implement same-asset cooldown layer, then v1.11-G: wire to pre_send_gate for test channel only.

## 6. Security Verification

| Check | Status |
|-------|--------|
| TG send | NONE |
| Formal channel touched | NONE |
| Secrets loaded | NONE |
| Token/chat_id/key read/printed | NONE |
| Paid API calls | NONE |
| Loop/daemon/cron started | NONE |
| Files deleted | NONE |
| Pre_send_gate connected | NONE |

## 7. Files Produced

- `scripts/run_market_radar_signal_value_gate_v111e_small_batch_dryrun.py`
- `results/market_radar_v111e_small_batch_dryrun_result.json`
- `runs/market_radar/v111e_small_batch_dryrun.md` (this file)
- `runs/market_radar/v111e_small_batch_dryrun_handoff.md`
