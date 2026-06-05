# v115O Whale Operator Evidence Collection Kit

**Generated**: 2026-06-05T09:10:22.927479+08:00

## Overview

- **Total addresses**: 4
- **High priority (manual attribution)**: 2
- **Medium priority (corroboration)**: 2
- **Manual attribution required**: 2
- **Corroboration required**: 2

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

## Preflight Command

```bash
python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py
```

Run this preflight FIRST after filling v115F workbook. It checks field completeness.

## Next Gate Command Order (Enforced — Only After Preflight Pass)

1. `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
2. `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
3. `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
4. `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

---

## High Priority Manual Attribution

**Count**: 2

These addresses are **unknown whales** with low confidence. The operator MUST manually research and establish entity identity before any confidence upgrade can proceed.

### 1. Unknown HYPE Whale

- **Address**: `0x082e843a431aef031264dc232693dd710aedca88`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high

#### Current Status

- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**
- **Blocked**: YES — workbook fields are empty, missing 7 required evidence items

#### Why Blocked

The v115F workbook for this address is empty. All operator-managed evidence fields are blank:

- `trusted_source_label_value`: **EMPTY**
- `trusted_source_url_or_note`: **EMPTY**
- `second_source_label_value`: **EMPTY**
- `second_source_url_or_note`: **EMPTY**
- `activity_pattern_note`: **EMPTY**
- `operator_confirmed_label`: **EMPTY**
- `operator_confidence_assessment`: **EMPTY**
- `reviewer`: **EMPTY**
- `reviewed_at`: **EMPTY**
- `ready_for_upgrade`: **EMPTY**

#### What to Research

Establish entity identity for Unknown HYPE Whale (0x082e843a431aef031264dc232693dd710aedca88). This address is currently unknown/low confidence. The operator MUST manually research and determine which entity or individual controls this address using trusted primary sources, independent secondary corroboration, and on-chain activity pattern analysis.

#### Required Evidence Bundle

- [ ] trusted_primary_source
- [ ] independent_second_source_or_cross_source
- [ ] activity_pattern_note
- [ ] operator_confirmation
- [ ] reviewer
- [ ] reviewed_at
- [ ] ready_for_upgrade

#### Primary Source Checklist (at least 1 required)

- [ ] Project/Team Official Docs or Disclosure (primary_project_official_docs)
- [ ] Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- [ ] Reputable Block Explorer Label (primary_reputable_explorer_label)
- [ ] Public Signed Statement by Entity/Operator (primary_signed_statement)
- [ ] Internally Verified Historical Label Record (primary_internal_verified_label)

#### Secondary Source Checklist (at least 1 required)

- [ ] Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- [ ] Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- [ ] Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- [ ] Public Social Identity Linkage (secondary_social_identity_linkage)
- [ ] Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

#### Activity Pattern Checklist (at least 1 required)

- [ ] Consistent Counterparty Pattern (activity_counterparty_pattern)
- [ ] Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- [ ] Position Behavior Consistency (activity_position_consistency)
- [ ] Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

#### Forbidden Source Types (DO NOT USE)

- ❌ Unsourced Social Post
- ❌ Single Anonymous Claim
- ❌ AI-Generated Attribution Without Source
- ❌ Screenshot Without Verifiable URL or Note
- ❌ Stale Label Without Update Date
- ❌ Label Copied from TG/Chat Without Evidence
- ❌ Vague 'Whale Said to Be X' Style Notes

#### Workbook Fields to Fill

File: `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv`

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

#### Minimum Pass Condition

Cannot upgrade from unknown/low unless ALL required evidence fields are complete (trusted_primary_source + independent_second_source + activity_pattern_note + operator_confirmation + reviewer + reviewed_at + ready_for_upgrade=true) AND no rejected source is present as core evidence. At least one primary_source is REQUIRED before any upgrade.

#### After Filling Workbook

1. Run preflight: `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
2. If preflight passes, rerun gates in order:
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

---

### 2. Unknown Hyperliquid Whale

- **Address**: `0x50b309f78e774a756a2230e1769729094cac9f20`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high

#### Current Status

- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**
- **Blocked**: YES — workbook fields are empty, missing 7 required evidence items

#### Why Blocked

The v115F workbook for this address is empty. All operator-managed evidence fields are blank:

- `trusted_source_label_value`: **EMPTY**
- `trusted_source_url_or_note`: **EMPTY**
- `second_source_label_value`: **EMPTY**
- `second_source_url_or_note`: **EMPTY**
- `activity_pattern_note`: **EMPTY**
- `operator_confirmed_label`: **EMPTY**
- `operator_confidence_assessment`: **EMPTY**
- `reviewer`: **EMPTY**
- `reviewed_at`: **EMPTY**
- `ready_for_upgrade`: **EMPTY**

#### What to Research

Establish entity identity for Unknown Hyperliquid Whale (0x50b309f78e774a756a2230e1769729094cac9f20). This address is currently unknown/low confidence. The operator MUST manually research and determine which entity or individual controls this address using trusted primary sources, independent secondary corroboration, and on-chain activity pattern analysis.

#### Required Evidence Bundle

- [ ] trusted_primary_source
- [ ] independent_second_source_or_cross_source
- [ ] activity_pattern_note
- [ ] operator_confirmation
- [ ] reviewer
- [ ] reviewed_at
- [ ] ready_for_upgrade

#### Primary Source Checklist (at least 1 required)

- [ ] Project/Team Official Docs or Disclosure (primary_project_official_docs)
- [ ] Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- [ ] Reputable Block Explorer Label (primary_reputable_explorer_label)
- [ ] Public Signed Statement by Entity/Operator (primary_signed_statement)
- [ ] Internally Verified Historical Label Record (primary_internal_verified_label)

#### Secondary Source Checklist (at least 1 required)

- [ ] Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- [ ] Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- [ ] Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- [ ] Public Social Identity Linkage (secondary_social_identity_linkage)
- [ ] Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

#### Activity Pattern Checklist (at least 1 required)

- [ ] Consistent Counterparty Pattern (activity_counterparty_pattern)
- [ ] Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- [ ] Position Behavior Consistency (activity_position_consistency)
- [ ] Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

#### Forbidden Source Types (DO NOT USE)

- ❌ Unsourced Social Post
- ❌ Single Anonymous Claim
- ❌ AI-Generated Attribution Without Source
- ❌ Screenshot Without Verifiable URL or Note
- ❌ Stale Label Without Update Date
- ❌ Label Copied from TG/Chat Without Evidence
- ❌ Vague 'Whale Said to Be X' Style Notes

#### Workbook Fields to Fill

File: `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv`

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

#### Minimum Pass Condition

Cannot upgrade from unknown/low unless ALL required evidence fields are complete (trusted_primary_source + independent_second_source + activity_pattern_note + operator_confirmation + reviewer + reviewed_at + ready_for_upgrade=true) AND no rejected source is present as core evidence. At least one primary_source is REQUIRED before any upgrade.

#### After Filling Workbook

1. Run preflight: `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
2. If preflight passes, rerun gates in order:
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

---

## Medium Priority Corroboration

**Count**: 2

These addresses have medium confidence labels. Additional corroborating evidence is needed to reach high confidence. They **CANNOT** go directly to TG test group.

### 1. Matrixport Related

- **Address**: `0x6c8512516ce5669d35113a11ca8b8de322fd84f6`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium

#### Current Status

- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**
- **Blocked**: YES — workbook fields are empty, missing 7 required evidence items

#### Why Blocked

The v115F workbook for this address is empty. All operator-managed evidence fields are blank:

- `trusted_source_label_value`: **EMPTY**
- `trusted_source_url_or_note`: **EMPTY**
- `second_source_label_value`: **EMPTY**
- `second_source_url_or_note`: **EMPTY**
- `activity_pattern_note`: **EMPTY**
- `operator_confirmed_label`: **EMPTY**
- `operator_confidence_assessment`: **EMPTY**
- `reviewer`: **EMPTY**
- `reviewed_at`: **EMPTY**
- `ready_for_upgrade`: **EMPTY**

#### What to Research

Corroborate existing medium-confidence label for Matrixport Related (0x6c8512516ce5669d35113a11ca8b8de322fd84f6). This address has a medium confidence label. The operator MUST find additional corroborating evidence from primary sources, independent secondary sources, and document activity patterns consistent with the claimed identity. Medium labels CANNOT go directly to TG test group.

#### Required Evidence Bundle

- [ ] trusted_primary_source_or_existing_label_source
- [ ] independent_second_source_or_cross_source
- [ ] activity_pattern_note
- [ ] operator_confirmation
- [ ] reviewer
- [ ] reviewed_at
- [ ] ready_for_upgrade

#### Primary Source Checklist (at least 1 required)

- [ ] Project/Team Official Docs or Disclosure (primary_project_official_docs)
- [ ] Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- [ ] Reputable Block Explorer Label (primary_reputable_explorer_label)
- [ ] Public Signed Statement by Entity/Operator (primary_signed_statement)
- [ ] Internally Verified Historical Label Record (primary_internal_verified_label)

#### Secondary Source Checklist (at least 1 required)

- [ ] Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- [ ] Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- [ ] Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- [ ] Public Social Identity Linkage (secondary_social_identity_linkage)
- [ ] Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

#### Activity Pattern Checklist (at least 1 required)

- [ ] Consistent Counterparty Pattern (activity_counterparty_pattern)
- [ ] Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- [ ] Position Behavior Consistency (activity_position_consistency)
- [ ] Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

#### Forbidden Source Types (DO NOT USE)

- ❌ Unsourced Social Post
- ❌ Single Anonymous Claim
- ❌ AI-Generated Attribution Without Source
- ❌ Screenshot Without Verifiable URL or Note
- ❌ Stale Label Without Update Date
- ❌ Label Copied from TG/Chat Without Evidence
- ❌ Vague 'Whale Said to Be X' Style Notes

#### Workbook Fields to Fill

File: `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv`

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

#### Minimum Pass Condition

Medium label CANNOT enter TG test group until corroboration passes the full HC_REQ_001 through HC_REQ_009 scoring checklist AND adjudication gate approves the upgrade to high confidence. All required evidence fields must be complete.

#### After Filling Workbook

1. Run preflight: `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
2. If preflight passes, rerun gates in order:
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

---

### 2. loraclexyz

- **Address**: `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium

#### Current Status

- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**
- **Blocked**: YES — workbook fields are empty, missing 7 required evidence items

#### Why Blocked

The v115F workbook for this address is empty. All operator-managed evidence fields are blank:

- `trusted_source_label_value`: **EMPTY**
- `trusted_source_url_or_note`: **EMPTY**
- `second_source_label_value`: **EMPTY**
- `second_source_url_or_note`: **EMPTY**
- `activity_pattern_note`: **EMPTY**
- `operator_confirmed_label`: **EMPTY**
- `operator_confidence_assessment`: **EMPTY**
- `reviewer`: **EMPTY**
- `reviewed_at`: **EMPTY**
- `ready_for_upgrade`: **EMPTY**

#### What to Research

Corroborate existing medium-confidence label for loraclexyz (0x8def9f50456c6c4e37fa5d3d57f108ed23992dae). This address has a medium confidence label. The operator MUST find additional corroborating evidence from primary sources, independent secondary sources, and document activity patterns consistent with the claimed identity. Medium labels CANNOT go directly to TG test group.

#### Required Evidence Bundle

- [ ] trusted_primary_source_or_existing_label_source
- [ ] independent_second_source_or_cross_source
- [ ] activity_pattern_note
- [ ] operator_confirmation
- [ ] reviewer
- [ ] reviewed_at
- [ ] ready_for_upgrade

#### Primary Source Checklist (at least 1 required)

- [ ] Project/Team Official Docs or Disclosure (primary_project_official_docs)
- [ ] Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- [ ] Reputable Block Explorer Label (primary_reputable_explorer_label)
- [ ] Public Signed Statement by Entity/Operator (primary_signed_statement)
- [ ] Internally Verified Historical Label Record (primary_internal_verified_label)

#### Secondary Source Checklist (at least 1 required)

- [ ] Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- [ ] Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- [ ] Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- [ ] Public Social Identity Linkage (secondary_social_identity_linkage)
- [ ] Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

#### Activity Pattern Checklist (at least 1 required)

- [ ] Consistent Counterparty Pattern (activity_counterparty_pattern)
- [ ] Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- [ ] Position Behavior Consistency (activity_position_consistency)
- [ ] Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

#### Forbidden Source Types (DO NOT USE)

- ❌ Unsourced Social Post
- ❌ Single Anonymous Claim
- ❌ AI-Generated Attribution Without Source
- ❌ Screenshot Without Verifiable URL or Note
- ❌ Stale Label Without Update Date
- ❌ Label Copied from TG/Chat Without Evidence
- ❌ Vague 'Whale Said to Be X' Style Notes

#### Workbook Fields to Fill

File: `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv`

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

#### Minimum Pass Condition

Medium label CANNOT enter TG test group until corroboration passes the full HC_REQ_001 through HC_REQ_009 scoring checklist AND adjudication gate approves the upgrade to high confidence. All required evidence fields must be complete.

#### After Filling Workbook

1. Run preflight: `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
2. If preflight passes, rerun gates in order:
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

---

## Rejected Source Warning

The following evidence sources **MUST NOT** be used to support label confidence upgrades:

1. **Unsourced Social Post** (`rejected_unsourced_social_post`)
2. **Single Anonymous Claim** (`rejected_single_anonymous_claim`)
3. **AI-Generated Attribution Without Source** (`rejected_ai_attribution`)
4. **Screenshot Without Verifiable URL or Note** (`rejected_screenshot_without_url`)
5. **Stale Label Without Update Date** (`rejected_stale_label_no_date`)
6. **Label Copied from TG/Chat Without Evidence** (`rejected_tg_chat_label`)
7. **Vague 'Whale Said to Be X' Style Notes** (`rejected_vague_whale_claim`)

> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked with REJECTED_EVIDENCE_ONLY block reason.
