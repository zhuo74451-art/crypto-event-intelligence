# v115R Whale Operator Real Workbook Submission Validation Report

**Generated**: 2026-06-05T09:38:15.383862+08:00
**Version**: v115R

## Executive Summary

- **Real workbook rows**: 4
- **Validation records**: 4
- **Validation decisions**: 4
- **Submission ready**: 0
- **Submission blocked**: 4
- **Ready for v115O preflight**: 0
- **Ready for gate rerun**: 0
- **TEST_ONLY contamination hits**: 0
- **Fixture value contamination hits**: 0
- **Rejected source hits**: 0
- **Safe rerun allowed**: **False**

## ⚠️ Critical Finding

**ALL 4 addresses are currently SUBMISSION BLOCKED.**

The real v115F workbook is empty — all operator-managed evidence fields are blank. No address has any completed real evidence.

### What This Means

- **Submission NOT valid**: All addresses fail field completeness checks.
- **v115O preflight NOT runnable**: Preflight would block all addresses in the current state.
- **Gate rerun NOT permitted**: v115G → v115L → v115H → v115M must not be run.
- **TG test group NOT accessible**: No address can enter TG test group.
- **Operator action required**: Fill v115F workbook with real evidence, then validate.

## Safety Status

| Item | Status |
|------|--------|
| Workbook modified | **false** |
| Real label upgrade performed | **false** |
| Real send candidate generated | **false** |
| Send ready | **false** |
| TG test group ready | **false** |
| TG sent | **false** |
| Prod state write | **false** |
| External API called | **false** |
| Credentials read | **false** |
| Workbook SHA-256 | `5accb61ded189c02...` |

---

## Per-Address Validation Results

| # | Address | Label | Confidence | Submission Ready | Missing Fields | TEST_ONLY | Fixture | Rejected |
|---|---------|-------|------------|------------------|----------------|-----------|---------|----------|
| 1 | 0x082e843a... | Unknown HYPE Whale | low | **False** | 10 | 0 | 0 | 0 |
| 2 | 0x50b309f7... | Unknown Hyperliquid Whale | low | **False** | 10 | 0 | 0 | 0 |
| 3 | 0x6c851251... | Matrixport Related | medium | **False** | 10 | 0 | 0 | 0 |
| 4 | 0x8def9f50... | loraclexyz | medium | **False** | 10 | 0 | 0 | 0 |

### 1. Unknown HYPE Whale

- **Address**: `0x082e843a431aef031264dc232693dd710aedca88`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high
- **Submission Ready**: **False**
- **Ready for v115O Preflight**: **False**
- **Ready for Gate Rerun**: **False**

#### Blocking Reasons

- `missing_required_fields`
- `reviewer_missing`
- `reviewed_at_missing`
- `operator_confirmation_missing`
- `operator_confidence_assessment_missing`
- `ready_for_upgrade_not_true`
- `unknown_whale_requires_manual_attribution`
- `low_confidence_label_not_sendable`
- `full_evidence_pack_required_for_low_unknown`

#### Missing Required Fields

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Contamination Detection

- **TEST_ONLY contamination hits**: 0
- **Fixture value contamination hits**: 0

#### Rejected Source Detection

- **Rejected source hits**: 0

#### Operator Review Validation

- **Reviewer validation**: **False**
- **Reviewed_at validation**: **False**
- **Operator confirmation validation**: **False**
- **Activity pattern validation**: **False**

#### Recommended Next Step

Operator must fill 10 missing required fields, clear 0 TEST_ONLY contaminations, clear 0 fixture contaminations, and clear 0 rejected source hits in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before resubmitting. Do NOT rerun gates until submission is validated.

---

### 2. Unknown Hyperliquid Whale

- **Address**: `0x50b309f78e774a756a2230e1769729094cac9f20`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high
- **Submission Ready**: **False**
- **Ready for v115O Preflight**: **False**
- **Ready for Gate Rerun**: **False**

#### Blocking Reasons

- `missing_required_fields`
- `reviewer_missing`
- `reviewed_at_missing`
- `operator_confirmation_missing`
- `operator_confidence_assessment_missing`
- `ready_for_upgrade_not_true`
- `unknown_whale_requires_manual_attribution`
- `low_confidence_label_not_sendable`
- `full_evidence_pack_required_for_low_unknown`

#### Missing Required Fields

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Contamination Detection

- **TEST_ONLY contamination hits**: 0
- **Fixture value contamination hits**: 0

#### Rejected Source Detection

- **Rejected source hits**: 0

#### Operator Review Validation

- **Reviewer validation**: **False**
- **Reviewed_at validation**: **False**
- **Operator confirmation validation**: **False**
- **Activity pattern validation**: **False**

#### Recommended Next Step

Operator must fill 10 missing required fields, clear 0 TEST_ONLY contaminations, clear 0 fixture contaminations, and clear 0 rejected source hits in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before resubmitting. Do NOT rerun gates until submission is validated.

---

### 3. Matrixport Related

- **Address**: `0x6c8512516ce5669d35113a11ca8b8de322fd84f6`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium
- **Submission Ready**: **False**
- **Ready for v115O Preflight**: **False**
- **Ready for Gate Rerun**: **False**

#### Blocking Reasons

- `missing_required_fields`
- `reviewer_missing`
- `reviewed_at_missing`
- `operator_confirmation_missing`
- `operator_confidence_assessment_missing`
- `ready_for_upgrade_not_true`
- `medium_confidence_requires_corroboration`
- `medium_cannot_direct_tg_test_group`

#### Missing Required Fields

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Contamination Detection

- **TEST_ONLY contamination hits**: 0
- **Fixture value contamination hits**: 0

#### Rejected Source Detection

- **Rejected source hits**: 0

#### Operator Review Validation

- **Reviewer validation**: **False**
- **Reviewed_at validation**: **False**
- **Operator confirmation validation**: **False**
- **Activity pattern validation**: **False**

#### Recommended Next Step

Operator must fill 10 missing required fields, clear 0 TEST_ONLY contaminations, clear 0 fixture contaminations, and clear 0 rejected source hits in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before resubmitting. Do NOT rerun gates until submission is validated.

---

### 4. loraclexyz

- **Address**: `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium
- **Submission Ready**: **False**
- **Ready for v115O Preflight**: **False**
- **Ready for Gate Rerun**: **False**

#### Blocking Reasons

- `missing_required_fields`
- `reviewer_missing`
- `reviewed_at_missing`
- `operator_confirmation_missing`
- `operator_confidence_assessment_missing`
- `ready_for_upgrade_not_true`
- `medium_confidence_requires_corroboration`
- `medium_cannot_direct_tg_test_group`

#### Missing Required Fields

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Contamination Detection

- **TEST_ONLY contamination hits**: 0
- **Fixture value contamination hits**: 0

#### Rejected Source Detection

- **Rejected source hits**: 0

#### Operator Review Validation

- **Reviewer validation**: **False**
- **Reviewed_at validation**: **False**
- **Operator confirmation validation**: **False**
- **Activity pattern validation**: **False**

#### Recommended Next Step

Operator must fill 10 missing required fields, clear 0 TEST_ONLY contaminations, clear 0 fixture contaminations, and clear 0 rejected source hits in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before resubmitting. Do NOT rerun gates until submission is validated.

---

## Why Safe Rerun Is Currently Blocked

Safe rerun is blocked because **4 of 4** addresses are not submission-ready.

### Pre-conditions for safe rerun

1. **All 4 addresses must be submission_ready=true** (all required fields filled with real, verified evidence).
2. **No TEST_ONLY or fixture values** in any field.
3. **No rejected sources** used as core evidence.
4. **Operator confirmation complete** for all addresses (label, assessment, reviewer, reviewed_at, ready_for_upgrade).
5. **Run v115O preflight first** after filling the workbook.
6. **Only after preflight passes**, rerun gates in enforced order:
   - `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`
7. **Medium confidence addresses CANNOT go directly to TG test group** even after gate pass.
