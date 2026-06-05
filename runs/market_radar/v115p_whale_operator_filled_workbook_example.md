# v115P Whale Operator Filled Workbook Example

**Generated**: 2026-06-05T09:12:22+08:00

## ⚠️ CRITICAL WARNING — FIXTURE ONLY

**ALL evidence values in this document and the companion fixture workbook are synthetic TEST_ONLY examples.**

- They are NOT real evidence.
- They demonstrate the FORMAT and STRUCTURE of correctly filled fields.
- **DO NOT** copy these values into the real v115F workbook.
- A real operator MUST replace every `TEST_ONLY_...` placeholder with actual verified sources obtained through manual research.
- Using fixture values as real evidence would constitute fabricated evidence.

---

## Overview

This document shows, for each of the 4 addresses in the v115F workbook, what a correctly filled evidence row looks like. It is a reference for operators to understand:

1. Which fields must be filled
2. Why each field matters
3. The difference between low/unknown whale and medium confidence requirements
4. The correct format for each field

---

## Address 1: Unknown HYPE Whale

- **Address**: `0x082e843a431aef031264dc232693dd710aedca88`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high

### Research Goal

This is a **low/unknown whale** address. The operator must establish entity identity through manual research using trusted primary sources, independent secondary corroboration, and on-chain activity pattern analysis.

### Required Evidence Fields

| # | Field | Why Required | Fixture Value |
|---|-------|-------------|---------------|
| 1 | `trusted_source_label_value` | Primary source that identifies the address entity | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: HyperLiquid Posi...` |
| 2 | `trusted_source_url_or_note` | URL or documentation for the primary source | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Verified block explorer l...` |
| 3 | `second_source_label_value` | Independent secondary source corroborating the identity | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Cross-Source Wall...` |
| 4 | `second_source_url_or_note` | URL or documentation for the secondary source | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Analytics dashboard label ...` |
| 5 | `activity_pattern_note` | On-chain behavior patterns consistent with claimed identity | `TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Consistent HYP...` |
| 6 | `operator_confirmed_label` | Operator's confirmed label after manual review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only manua...` |
| 7 | `operator_confidence_assessment` | Operator's confidence assessment after evidence review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only asses...` |
| 8 | `reviewer` | Identifier of the reviewing operator | `TEST_ONLY_REVIEWER` |
| 9 | `reviewed_at` | Timestamp when review was completed | `TEST_ONLY_REVIEWED_AT_2026-06-05` |
| 10 | `ready_for_upgrade` | Boolean flag set by operator | `true` |

### Confidence-Specific Requirements

**Low/Unknown Whale Requirements:**

- MUST have trusted primary source establishing entity identity
- MUST have independent second source or cross-source corroboration
- MUST have activity pattern note documenting on-chain behavior
- MUST have operator confirmation (label + confidence assessment + reviewer + timestamp)
- `ready_for_upgrade` must be explicitly `true`
- At least one `primary_source` is REQUIRED before any upgrade
- Cannot upgrade from unknown/low unless ALL required evidence fields are complete
- No rejected source may be used as core evidence

---

## Address 2: Unknown Hyperliquid Whale

- **Address**: `0x50b309f78e774a756a2230e1769729094cac9f20`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high

### Research Goal

This is a **low/unknown whale** address. The operator must establish entity identity through manual research using trusted primary sources, independent secondary corroboration, and on-chain activity pattern analysis.

### Required Evidence Fields

| # | Field | Why Required | Fixture Value |
|---|-------|-------------|---------------|
| 1 | `trusted_source_label_value` | Primary source that identifies the address entity | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: HyperLiquid Posi...` |
| 2 | `trusted_source_url_or_note` | URL or documentation for the primary source | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Verified block explorer l...` |
| 3 | `second_source_label_value` | Independent secondary source corroborating the identity | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Cross-Source Wall...` |
| 4 | `second_source_url_or_note` | URL or documentation for the secondary source | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Analytics dashboard label ...` |
| 5 | `activity_pattern_note` | On-chain behavior patterns consistent with claimed identity | `TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Consistent HYP...` |
| 6 | `operator_confirmed_label` | Operator's confirmed label after manual review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only manua...` |
| 7 | `operator_confidence_assessment` | Operator's confidence assessment after evidence review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only asses...` |
| 8 | `reviewer` | Identifier of the reviewing operator | `TEST_ONLY_REVIEWER` |
| 9 | `reviewed_at` | Timestamp when review was completed | `TEST_ONLY_REVIEWED_AT_2026-06-05` |
| 10 | `ready_for_upgrade` | Boolean flag set by operator | `true` |

### Confidence-Specific Requirements

**Low/Unknown Whale Requirements:**

- MUST have trusted primary source establishing entity identity
- MUST have independent second source or cross-source corroboration
- MUST have activity pattern note documenting on-chain behavior
- MUST have operator confirmation (label + confidence assessment + reviewer + timestamp)
- `ready_for_upgrade` must be explicitly `true`
- At least one `primary_source` is REQUIRED before any upgrade
- Cannot upgrade from unknown/low unless ALL required evidence fields are complete
- No rejected source may be used as core evidence

---

## Address 3: Matrixport Related

- **Address**: `0x6c8512516ce5669d35113a11ca8b8de322fd84f6`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium

### Research Goal

This is a **medium confidence** address. The operator must corroborate the existing label with additional evidence from primary sources, independent secondary sources, and activity pattern documentation. **Medium labels CANNOT go directly to TG test group.** They must pass additional gates (v115G → v115L → v115H → v115M) even after preflight passes.

### Required Evidence Fields

| # | Field | Why Required | Fixture Value |
|---|-------|-------------|---------------|
| 1 | `trusted_source_label_value` | Primary source that identifies the address entity | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Existing label s...` |
| 2 | `trusted_source_url_or_note` | URL or documentation for the primary source | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Verified public label pag...` |
| 3 | `second_source_label_value` | Independent secondary source corroborating the identity | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Independent cross...` |
| 4 | `second_source_url_or_note` | URL or documentation for the secondary source | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Cross-source corroboration...` |
| 5 | `activity_pattern_note` | On-chain behavior patterns consistent with claimed identity | `TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Position behav...` |
| 6 | `operator_confirmed_label` | Operator's confirmed label after manual review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only corro...` |
| 7 | `operator_confidence_assessment` | Operator's confidence assessment after evidence review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only asses...` |
| 8 | `reviewer` | Identifier of the reviewing operator | `TEST_ONLY_REVIEWER` |
| 9 | `reviewed_at` | Timestamp when review was completed | `TEST_ONLY_REVIEWED_AT_2026-06-05` |
| 10 | `ready_for_upgrade` | Boolean flag set by operator | `true` |

### Confidence-Specific Requirements

**Medium Confidence Requirements:**

- MUST have trusted primary source OR verified existing label source
- MUST have independent second source or cross-source corroboration
- MUST have activity pattern note documenting on-chain behavior
- MUST have operator confirmation (label + confidence assessment + reviewer + timestamp)
- `ready_for_upgrade` must be explicitly `true`
- **Medium passing preflight does NOT equal TG test group readiness**
- Additional gates (v115G → v115L → v115H → v115M) must still be run
- All HC_REQ_001 through HC_REQ_009 must pass for high confidence upgrade

---

## Address 4: loraclexyz

- **Address**: `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium

### Research Goal

This is a **medium confidence** address. The operator must corroborate the existing label with additional evidence from primary sources, independent secondary sources, and activity pattern documentation. **Medium labels CANNOT go directly to TG test group.** They must pass additional gates (v115G → v115L → v115H → v115M) even after preflight passes.

### Required Evidence Fields

| # | Field | Why Required | Fixture Value |
|---|-------|-------------|---------------|
| 1 | `trusted_source_label_value` | Primary source that identifies the address entity | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Existing label s...` |
| 2 | `trusted_source_url_or_note` | URL or documentation for the primary source | `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Verified public label pag...` |
| 3 | `second_source_label_value` | Independent secondary source corroborating the identity | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Independent cross...` |
| 4 | `second_source_url_or_note` | URL or documentation for the secondary source | `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE — Cross-source corroboration...` |
| 5 | `activity_pattern_note` | On-chain behavior patterns consistent with claimed identity | `TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE — Example: Position behav...` |
| 6 | `operator_confirmed_label` | Operator's confirmed label after manual review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only corro...` |
| 7 | `operator_confidence_assessment` | Operator's confidence assessment after evidence review | `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE — Fixture-only asses...` |
| 8 | `reviewer` | Identifier of the reviewing operator | `TEST_ONLY_REVIEWER` |
| 9 | `reviewed_at` | Timestamp when review was completed | `TEST_ONLY_REVIEWED_AT_2026-06-05` |
| 10 | `ready_for_upgrade` | Boolean flag set by operator | `true` |

### Confidence-Specific Requirements

**Medium Confidence Requirements:**

- MUST have trusted primary source OR verified existing label source
- MUST have independent second source or cross-source corroboration
- MUST have activity pattern note documenting on-chain behavior
- MUST have operator confirmation (label + confidence assessment + reviewer + timestamp)
- `ready_for_upgrade` must be explicitly `true`
- **Medium passing preflight does NOT equal TG test group readiness**
- Additional gates (v115G → v115L → v115H → v115M) must still be run
- All HC_REQ_001 through HC_REQ_009 must pass for high confidence upgrade

---

## How a Real Operator Should Use This Example

1. **Do NOT copy fixture values.** All fixture values are synthetic placeholders.
2. **Research each address manually.** Use the evidence source registry (v115K) to identify acceptable primary, secondary, and activity sources.
3. **Fill the real v115F workbook.** Replace each `TEST_ONLY_...` value with real, verifiable evidence.
4. **Run v115O preflight first.** After filling the real workbook, run `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py` to verify completeness.
5. **Only if preflight passes**, rerun gates in order: v115G → v115L → v115H → v115M.
6. **Do NOT skip preflight.** Running gates without preflight pass will result in blocks.

## Rejected Source Warning

The following sources **MUST NOT** be used as core evidence:

1. **Unsourced Social Post**
2. **Single Anonymous Claim**
3. **AI-Generated Attribution Without Source**
4. **Screenshot Without Verifiable URL or Note**
5. **Stale Label Without Update Date**
6. **Label Copied from TG/Chat Without Evidence**
7. **Vague 'Whale Said to Be X' Style Notes**

> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked with REJECTED_EVIDENCE_ONLY block reason.
