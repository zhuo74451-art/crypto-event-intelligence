# v115Q Whale Fixture Filled Workbook — End-to-End Gate Replay Report

**Generated**: 2026-06-05T09:30:00+08:00

## ⚠️ CRITICAL WARNING — FIXTURE ONLY

**This entire report documents a FIXTURE-ONLY gate replay.**

- ALL evidence values are NOT real — they are synthetic `TEST_ONLY` placeholders from the v115P fixture workbook.
- **Fixture replay passing does NOT mean real address evidence has been verified.**
- **No real label upgrades have been performed.**
- **Real v115F workbook evidence fields remain empty and blocked.**
- **TG test group delivery is still NOT allowed.**
- **No send candidate has been generated.**

---

## Executive Summary

The v115Q fixture-only end-to-end gate replay demonstrates that the full gate pipeline
(v115G intake → v115L scoring → v115H adjudication → v115M workflow) correctly passes
when all evidence fields are complete in the workbook.

### Key Results

| Metric | Value |
|--------|-------|
| Fixture rows | 4 |
| Fixture intake ready count | 4 |
| Fixture scoring passed count | 4 |
| Fixture adjudication ready count | 4 |
| Fixture workflow ready count | 4 |
| Fixture upgrade preview allowed count | 4 |
| Low/unknown fixture workflow ready | 2 |
| Medium fixture workflow ready | 2 |
| Manual attribution fixture ready | 2 |
| Corroboration fixture ready | 2 |
| Real workbook rows | 4 |
| Real workbook modified | **False** |
| Real label upgrade performed | **False** |
| Real send candidate generated | **False** |
| Send ready | **False** |
| TG test group ready | **False** |
| TG sent | **False** |
| Fixture only | **True** |
| Gate command order enforced | **True** |
| Real workbook byte-identical | **True** |

---

## Per-Address Gate Replay Results

### 1. Unknown HYPE Whale

- **Address**: `0x082e843a431aef031264dc232693dd710aedca88`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required

| Gate | Version | Replay Status | Ready |
|------|---------|---------------|-------|
| Intake | v115G | intake_passed | **True** |
| Evidence Scoring | v115L | scoring_passed | **True** |
| Adjudication | v115H | adjudication_passed | **True** |
| Workflow | v115M | workflow_passed | **True** |

- Evidence score replay: 9/9
- HC requirements passed: 9

**Low/Unknown Whale — Manual Attribution Required:**

- `manual_attribution_replay_ready`: **true**
- Requires: trusted_primary_source + independent_second_source_or_cross_source + activity_pattern_note + operator_confirmation
- **WARNING**: Fixture replay passing does NOT mean real manual attribution has been completed.
- Real operator must still manually research and establish entity identity with real verified sources.

> FIXTURE-ONLY REPLAY: Workflow preview replay passed with TEST_ONLY fixture evidence. upgrade_preview_replay_allowed = true means the gate replay logic is verified, NOT that real label upgrade is allowed. uprade_preview is a preview only. Real label upgrade, TG test group, and send candidate all remain false/blocked.

---

### 2. Unknown Hyperliquid Whale

- **Address**: `0x50b309f78e774a756a2230e1769729094cac9f20`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required

| Gate | Version | Replay Status | Ready |
|------|---------|---------------|-------|
| Intake | v115G | intake_passed | **True** |
| Evidence Scoring | v115L | scoring_passed | **True** |
| Adjudication | v115H | adjudication_passed | **True** |
| Workflow | v115M | workflow_passed | **True** |

- Evidence score replay: 9/9
- HC requirements passed: 9

**Low/Unknown Whale — Manual Attribution Required:**

- `manual_attribution_replay_ready`: **true**
- Requires: trusted_primary_source + independent_second_source_or_cross_source + activity_pattern_note + operator_confirmation
- **WARNING**: Fixture replay passing does NOT mean real manual attribution has been completed.
- Real operator must still manually research and establish entity identity with real verified sources.

> FIXTURE-ONLY REPLAY: Workflow preview replay passed with TEST_ONLY fixture evidence. upgrade_preview_replay_allowed = true means the gate replay logic is verified, NOT that real label upgrade is allowed. uprade_preview is a preview only. Real label upgrade, TG test group, and send candidate all remain false/blocked.

---

### 3. Matrixport Related

- **Address**: `0x6c8512516ce5669d35113a11ca8b8de322fd84f6`
- **Current Confidence**: medium
- **Action Type**: corroboration_required

| Gate | Version | Replay Status | Ready |
|------|---------|---------------|-------|
| Intake | v115G | intake_passed | **True** |
| Evidence Scoring | v115L | scoring_passed | **True** |
| Adjudication | v115H | adjudication_passed | **True** |
| Workflow | v115M | workflow_passed | **True** |

- Evidence score replay: 9/9
- HC requirements passed: 9

**Medium Confidence — Corroboration Required:**

- `corroboration_replay_ready`: **true**
- Requires: existing_label_source_or_trusted_primary_source + independent_second_source_or_cross_source + activity_pattern_note + operator_confirmation
- `must_not_claim_direct_tg_test_group_ready`: **true**
- **WARNING**: Medium confidence passing fixture replay does NOT equal TG test group readiness.
- Medium labels CANNOT go directly to TG test group even after real gate pass.
- All gates must pass with real evidence, then additional TG routing policies apply.

> FIXTURE-ONLY REPLAY: Workflow preview replay passed with TEST_ONLY fixture evidence. upgrade_preview_replay_allowed = true means the gate replay logic is verified, NOT that real label upgrade is allowed. uprade_preview is a preview only. Real label upgrade, TG test group, and send candidate all remain false/blocked.

---

### 4. loraclexyz

- **Address**: `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae`
- **Current Confidence**: medium
- **Action Type**: corroboration_required

| Gate | Version | Replay Status | Ready |
|------|---------|---------------|-------|
| Intake | v115G | intake_passed | **True** |
| Evidence Scoring | v115L | scoring_passed | **True** |
| Adjudication | v115H | adjudication_passed | **True** |
| Workflow | v115M | workflow_passed | **True** |

- Evidence score replay: 9/9
- HC requirements passed: 9

**Medium Confidence — Corroboration Required:**

- `corroboration_replay_ready`: **true**
- Requires: existing_label_source_or_trusted_primary_source + independent_second_source_or_cross_source + activity_pattern_note + operator_confirmation
- `must_not_claim_direct_tg_test_group_ready`: **true**
- **WARNING**: Medium confidence passing fixture replay does NOT equal TG test group readiness.
- Medium labels CANNOT go directly to TG test group even after real gate pass.
- All gates must pass with real evidence, then additional TG routing policies apply.

> FIXTURE-ONLY REPLAY: Workflow preview replay passed with TEST_ONLY fixture evidence. upgrade_preview_replay_allowed = true means the gate replay logic is verified, NOT that real label upgrade is allowed. uprade_preview is a preview only. Real label upgrade, TG test group, and send candidate all remain false/blocked.

---

## Safety Verification

| Item | Status |
|------|--------|
| Real workbook modified | **False** |
| Real label upgrade performed | **False** |
| Real send candidate generated | **False** |
| Send ready | **False** |
| TG test group ready | **False** |
| TG sent | **False** |
| Prod state write | **False** |
| External API called | **False** |
| Credentials read | **False** |
| Fixture only | **True** |
| Gate command order enforced | **True** |
| Real workbook byte-identical | **True** |

---

## What This Proves

1. **The gate pipeline is not 'forever blocked'.** When evidence fields are complete,
   all 4 gates (intake → scoring → adjudication → workflow) correctly pass.
2. **The gate logic correctly distinguishes low/unknown vs medium confidence paths.**
3. **Fixture replay passing ≠ real evidence passing.** Real addresses still require
   operator research with verifiable sources.
4. **The workflow is 'evidence-complete passable, real-evidence-missing stays blocked'**
   — exactly the closed-loop design intended.

## Next Steps for Real Operator

1. **Do NOT use fixture values.** All fixture evidence is synthetic TEST_ONLY.
2. **Manually research each address** using trusted primary, secondary, and activity
   sources per v115K evidence registry.
3. **Fill the real v115F workbook** with actual verified evidence.
4. **Run v115O preflight** to verify evidence completeness.
5. **Only after preflight passes**, run real gates in enforced order:
   - v115G intake → v115L scoring → v115H adjudication → v115M workflow
6. **Medium labels require additional TG routing review** even after gate pass.
