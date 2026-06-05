# v115F Whale Address Audit Operator Workbook

**Generated:** 2026-06-05T07:18:29.330910+08:00
**Stage:** v115f_whale_address_audit_operator_workbook_local_only
**Input:** v115E address audit evidence pack (4 audit forms)

---

## ⚠️ IMPORTANT: Read Before Continuing

1. **This is a LOCAL operator workbook for manual evidence collection only.**
2. **This file is NOT a trading signal, NOT a production send file, NOT a TG send candidate.**
3. **Do NOT upgrade any label confidence before ALL manual evidence fields have been filled.**
4. **Each address requires ALL 4 evidence types before label upgrade can proceed.**
5. **After filling evidence, a separate upgrade gate must be run — this workbook does NOT auto-upgrade labels.**

---

## 1. Current State Summary

| Metric | Value |
|--------|-------|
| Total addresses | 4 |
| upgrade_ready_count | 0 |
| blocked_upgrade_count | 4 |
| send_ready | [NO] false |
| tg_test_group_ready | [NO] false |
| local_review_ready | [OK] true |
| manual_fields_prefilled | [NO] false |
| external_api_called | [NO] false |
| credentials_read | [NO] false |
| tg_sent | [NO] false |
| prod_state_write | [NO] false |
| daemon_started | [NO] false |
| watcher_started | [NO] false |
| labels upgraded | **0 — NONE** |

**Status:** [BLOCKED] ALL 4 addresses are BLOCKED. No label has been upgraded to high confidence.
Manual operator evidence collection is required before any upgrade can proceed.

---

## 2. Address Audit Tables

### Address 1: `0x082e843a431aef031264dc232693dd710aedca88`

**Label:** Unknown HYPE Whale
**Confidence:** low → target: high
**Priority:** high
**upgrade_ready:** [NO] false
**send_allowed:** [NO] false
**tg_test_group_allowed:** [NO] false
**public_send_allowed:** [NO] false

#### Why This Address Matters
Address labeled as 'Unknown HYPE Whale' with low confidence. Linked to 1 position(s) on HyperLiquid. Delta types observed: size_changed. MEDIUM operator attention — notable position changes requiring review. Assets involved: HYPE.

#### Delta Context
```
HYPE/long:size_changed (Position size reduced versus local baseline (delta=-1,079,193.36); review delta )
```

#### Missing Evidence (4/4 required)
  - `trusted_source_label`
  - `cross_source_consistency`
  - `address_activity_consistency`
  - `manual_operator_confirmation`

#### Operator Actions Required
  1. MANUAL_LABEL_VERIFICATION: Research and confirm whale identity from trusted on-chain explorers or label providers.
  2. CROSS_SOURCE_CHECK: Find at least one independent second source confirming this address's identity.
  3. ACTIVITY_PATTERN_VERIFICATION: Review HyperLiquid position history for consistency with claimed identity.
  4. OPERATOR_CONFIRMATION: Explicitly sign off on label or reject with reason.

#### Manual Evidence Fields (all empty — operator must fill)
| Field | Value | Status |
|-------|-------|--------|
| `trusted_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `trusted_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `activity_pattern_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confirmed_label` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confidence_assessment` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_reject_reason` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewer` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewed_at` | *(empty — awaiting operator)* | [ ] Not filled |

#### Block Reasons
  - `UPGRADE_BLOCKED_MISSING_EVIDENCE`
  - `MANUAL_OPERATOR_EVIDENCE_REQUIRED`
  - `NO_TRUSTED_SOURCE_LABEL_PROVIDED`
  - `NO_CROSS_SOURCE_CONSISTENCY_VERIFIED`
  - `NO_ACTIVITY_PATTERN_VERIFIED`
  - `NO_OPERATOR_CONFIRMATION`
  - `UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION`
  - `LOW_CONFIDENCE_LABEL_NOT_SENDABLE`
  - `LABEL_CONFIDENCE_BELOW_HIGH`
  - `OPERATOR_APPROVAL_MISSING`
  - `TG_SEND_DISABLED_BY_DEFAULT`
  - `NOT_SEND_READY`
  - `UNKNOWN_WHALE_NOT_SENDABLE`
  - `LABEL_UPGRADE_REQUIRED`
  - `NO_HIGH_CONFIDENCE_LABELS_EXIST`

---

### Address 2: `0x50b309f78e774a756a2230e1769729094cac9f20`

**Label:** Unknown Hyperliquid Whale
**Confidence:** low → target: high
**Priority:** high
**upgrade_ready:** [NO] false
**send_allowed:** [NO] false
**tg_test_group_allowed:** [NO] false
**public_send_allowed:** [NO] false

#### Why This Address Matters
Address labeled as 'Unknown Hyperliquid Whale' with low confidence. Linked to 1 position(s) on HyperLiquid. Delta types observed: closed_position. HIGH operator attention — contains significant position change (e.g., closed_position). Assets involved: BTC.

#### Delta Context
```
BTC/short:closed_position (BTC short position disappeared in second probe; classify as closed_position for )
```

#### Missing Evidence (4/4 required)
  - `trusted_source_label`
  - `cross_source_consistency`
  - `address_activity_consistency`
  - `manual_operator_confirmation`

#### Operator Actions Required
  1. MANUAL_LABEL_VERIFICATION: Research and confirm whale identity from trusted on-chain explorers or label providers.
  2. CROSS_SOURCE_CHECK: Find at least one independent second source confirming this address's identity.
  3. ACTIVITY_PATTERN_VERIFICATION: Review HyperLiquid position history for consistency with claimed identity.
  4. OPERATOR_CONFIRMATION: Explicitly sign off on label or reject with reason.

#### Manual Evidence Fields (all empty — operator must fill)
| Field | Value | Status |
|-------|-------|--------|
| `trusted_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `trusted_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `activity_pattern_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confirmed_label` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confidence_assessment` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_reject_reason` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewer` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewed_at` | *(empty — awaiting operator)* | [ ] Not filled |

#### Block Reasons
  - `UPGRADE_BLOCKED_MISSING_EVIDENCE`
  - `MANUAL_OPERATOR_EVIDENCE_REQUIRED`
  - `NO_TRUSTED_SOURCE_LABEL_PROVIDED`
  - `NO_CROSS_SOURCE_CONSISTENCY_VERIFIED`
  - `NO_ACTIVITY_PATTERN_VERIFIED`
  - `NO_OPERATOR_CONFIRMATION`
  - `UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION`
  - `LOW_CONFIDENCE_LABEL_NOT_SENDABLE`
  - `LABEL_CONFIDENCE_BELOW_HIGH`
  - `OPERATOR_APPROVAL_MISSING`
  - `TG_SEND_DISABLED_BY_DEFAULT`
  - `NOT_SEND_READY`
  - `UNKNOWN_WHALE_NOT_SENDABLE`
  - `LABEL_UPGRADE_REQUIRED`
  - `NO_HIGH_CONFIDENCE_LABELS_EXIST`

---

### Address 3: `0x6c8512516ce5669d35113a11ca8b8de322fd84f6`

**Label:** Matrixport Related
**Confidence:** medium → target: high
**Priority:** medium
**upgrade_ready:** [NO] false
**send_allowed:** [NO] false
**tg_test_group_allowed:** [NO] false
**public_send_allowed:** [NO] false

#### Why This Address Matters
Address labeled as 'Matrixport Related' with medium confidence. Linked to 1 position(s) on HyperLiquid. Delta types observed: unchanged. Assets involved: ETH.

#### Delta Context
```
ETH/long:unchanged (Position remains within tolerance; low-priority observation.)
```

#### Missing Evidence (4/4 required)
  - `trusted_source_label`
  - `cross_source_consistency`
  - `address_activity_consistency`
  - `manual_operator_confirmation`

#### Operator Actions Required
  1. MANUAL_LABEL_VERIFICATION: Research and confirm whale identity from trusted on-chain explorers or label providers.
  2. CROSS_SOURCE_CHECK: Find at least one independent second source confirming this address's identity.
  3. ACTIVITY_PATTERN_VERIFICATION: Review HyperLiquid position history for consistency with claimed identity.
  4. OPERATOR_CONFIRMATION: Explicitly sign off on label or reject with reason.

#### Manual Evidence Fields (all empty — operator must fill)
| Field | Value | Status |
|-------|-------|--------|
| `trusted_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `trusted_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `activity_pattern_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confirmed_label` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confidence_assessment` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_reject_reason` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewer` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewed_at` | *(empty — awaiting operator)* | [ ] Not filled |

#### Block Reasons
  - `UPGRADE_BLOCKED_MISSING_EVIDENCE`
  - `MANUAL_OPERATOR_EVIDENCE_REQUIRED`
  - `NO_TRUSTED_SOURCE_LABEL_PROVIDED`
  - `NO_CROSS_SOURCE_CONSISTENCY_VERIFIED`
  - `NO_ACTIVITY_PATTERN_VERIFIED`
  - `NO_OPERATOR_CONFIRMATION`
  - `MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION`
  - `LABEL_CONFIDENCE_BELOW_HIGH`
  - `OPERATOR_APPROVAL_MISSING`
  - `TG_SEND_DISABLED_BY_DEFAULT`
  - `NOT_SEND_READY`
  - `NO_HIGH_CONFIDENCE_LABELS_EXIST`

---

### Address 4: `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae`

**Label:** loraclexyz
**Confidence:** medium → target: high
**Priority:** medium
**upgrade_ready:** [NO] false
**send_allowed:** [NO] false
**tg_test_group_allowed:** [NO] false
**public_send_allowed:** [NO] false

#### Why This Address Matters
Address labeled as 'loraclexyz' with medium confidence. Linked to 7 position(s) on HyperLiquid. Delta types observed: unchanged, size_changed. MEDIUM operator attention — notable position changes requiring review. Assets involved: ASTER, HYPE, NEAR, TON, WLD, XMR, ZEC.

#### Delta Context
```
ZEC/long:size_changed (Position size reduced versus local baseline (delta=-205,795.41); review delta ma) | HYPE/long:size_changed (Position size reduced versus local baseline (delta=-106,835.62); review delta ma) | TON/long:size_changed (Position size reduced versus local baseline (delta=-97,311.11); review delta mag) | WLD/long:size_changed (Position size reduced versus local baseline (delta=-69,489.12); review delta mag) | NEAR/long:unchanged (Position remains within tolerance; low-priority observation.) | XMR/long:unchanged (Position remains within tolerance; low-priority observation.) | ASTER/long:unchanged (Position remains within tolerance; low-priority observation.)
```

#### Missing Evidence (4/4 required)
  - `trusted_source_label`
  - `cross_source_consistency`
  - `address_activity_consistency`
  - `manual_operator_confirmation`

#### Operator Actions Required
  1. MANUAL_LABEL_VERIFICATION: Research and confirm whale identity from trusted on-chain explorers or label providers.
  2. CROSS_SOURCE_CHECK: Find at least one independent second source confirming this address's identity.
  3. ACTIVITY_PATTERN_VERIFICATION: Review HyperLiquid position history for consistency with claimed identity.
  4. OPERATOR_CONFIRMATION: Explicitly sign off on label or reject with reason.

#### Manual Evidence Fields (all empty — operator must fill)
| Field | Value | Status |
|-------|-------|--------|
| `trusted_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `trusted_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `activity_pattern_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confirmed_label` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confidence_assessment` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_reject_reason` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewer` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewed_at` | *(empty — awaiting operator)* | [ ] Not filled |

#### Block Reasons
  - `UPGRADE_BLOCKED_MISSING_EVIDENCE`
  - `MANUAL_OPERATOR_EVIDENCE_REQUIRED`
  - `NO_TRUSTED_SOURCE_LABEL_PROVIDED`
  - `NO_CROSS_SOURCE_CONSISTENCY_VERIFIED`
  - `NO_ACTIVITY_PATTERN_VERIFIED`
  - `NO_OPERATOR_CONFIRMATION`
  - `MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION`
  - `LABEL_CONFIDENCE_BELOW_HIGH`
  - `OPERATOR_APPROVAL_MISSING`
  - `TG_SEND_DISABLED_BY_DEFAULT`
  - `NOT_SEND_READY`
  - `NO_HIGH_CONFIDENCE_LABELS_EXIST`

---


## 3. Operator Filling Instructions

### How to Fill This Workbook

1. Open the accompanying CSV workbook: `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv`
2. For each address, collect evidence for ALL 4 required types:
   - **trusted_source_label**: Look up the address on trusted explorers (Etherscan, Nansen, Arkham, etc.)
   - **cross_source_consistency**: Find at least one independent second source confirming identity
   - **address_activity_consistency**: Review HyperLiquid position history for consistency
   - **manual_operator_confirmation**: After reviewing all evidence, explicitly confirm or reject
3. Fill in the corresponding CSV fields for each address
4. When ALL 4 evidence types are filled for an address, set `ready_for_upgrade` to `true`
5. After ALL addresses are reviewed, run the next upgrade gate stage

### Field Definitions

| CSV Column | Type | Instructions |
|------------|------|--------------|
| `trusted_source_label_value` | text | Label from trusted source (e.g., "Wintermute", "Jump Trading") |
| `trusted_source_url_or_note` | text | URL or note for the trusted source |
| `second_source_label_value` | text | Label from a second independent source |
| `second_source_url_or_note` | text | URL or note for the second source |
| `activity_pattern_note` | text | Notes on on-chain activity pattern consistency |
| `operator_confirmed_label` | text | Operator's final confirmed label |
| `operator_confidence_assessment` | text | Operator's confidence assessment (low/medium/high) |
| `operator_reject_reason` | text | If rejecting, reason for rejection |
| `reviewer` | text | Name/ID of the operator filling this row |
| `reviewed_at` | text | ISO timestamp when review was completed |
| `ready_for_upgrade` | bool | Set to `true` ONLY when ALL 4 evidence types are complete |
| `upgrade_ready` | bool | Set to `true` ONLY after operator confirms evidence is sufficient |
| `send_allowed` | bool | Do NOT set manually — gate-controlled |
| `tg_test_group_allowed` | bool | Do NOT set manually — gate-controlled |
| `public_send_allowed` | bool | Do NOT set manually — gate-controlled |

### ⚠️ Critical Constraints

- **Do NOT set `ready_for_upgrade` to `true` until ALL 4 evidence types are filled per address.**
- **Do NOT modify `send_allowed`, `tg_test_group_allowed`, or `public_send_allowed` — these are gate-controlled.**
- **Do NOT modify `block_reasons` — these are gate-generated.**
- **This is a LOCAL workbook only. Filling it does NOT automatically upgrade labels or send anything.**

---

## 4. Explicit NOT Declarations

This workbook is explicitly **NOT**:

- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A TG send candidate
- [NO] A label upgrade execution
- [NO] A send-ready assertion
- [NO] AI-generated evidence
- [NO] External API query results

This workbook **IS**:

- [OK] A local operator audit workbook
- [OK] A structured template for manual evidence collection
- [OK] Input for a future label upgrade gate (not yet run)
- [OK] Fully guarded — all send flags are false
- [OK] Traceable, verifiable, reproducible

---

*Generated by v115F runner. Local only. No external communication intended.*
