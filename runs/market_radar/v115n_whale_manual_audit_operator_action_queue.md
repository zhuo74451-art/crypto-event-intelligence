# v115N Whale Operator Action Queue

**Generated**: 2026-06-05T09:02:13.517868+08:00

## Overview

- **Total addresses**: 4
- **High priority (manual attribution)**: 2
- **Medium priority (corroboration)**: 2
- **Manual attribution required**: 2
- **Corroboration required**: 2

## Safety Status

| Item | Status |
|------|--------|
| Real workbook modified | **false** |
| Real label upgrade performed | **false** |
| Real send candidate generated | **false** |
| Send ready | **false** |
| TG test group ready | **false** |
| TG sent | **false** |
| Prod state write | **false** |
| External API called | **false** |
| Credentials read | **false** |

## Next Gate Command Order (Enforced)

1. `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
2. `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
3. `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
4. `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

---

## High Priority Actions (Manual Attribution Required)

**Count**: 2

These addresses are **unknown whales** with low confidence. The operator MUST manually
research and establish entity identity before any confidence upgrade can proceed.

### 1. Unknown HYPE Whale

- **Address**: `0x082e843a431aef031264dc232693dd710aedca88`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high
- **Blocked Stage**: intake_gate
- **Workbook Row Hint**: Row 2 in v115F workbook (CSV row 2, 1-based data row 1)

#### Blocked Reasons

- INTAKE_GATE_NOT_READY
- WORKFLOW_BLOCKED

#### Missing Workbook Fields

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

#### Recommended Source Types

**Primary Sources (at least 1 required):**
- Project/Team Official Docs or Disclosure (primary_project_official_docs)
- Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- Reputable Block Explorer Label (primary_reputable_explorer_label)
- Public Signed Statement by Entity/Operator (primary_signed_statement)
- Internally Verified Historical Label Record (primary_internal_verified_label)

**Secondary Sources (at least 1 required):**
- Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- Public Social Identity Linkage (secondary_social_identity_linkage)
- Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

**Activity Sources (at least 1 required):**
- Consistent Counterparty Pattern (activity_counterparty_pattern)
- Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- Position Behavior Consistency (activity_position_consistency)
- Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

> For unknown whale: MUST provide trusted primary source + second source/cross-source + activity pattern + operator confirmation. At least one primary_source is required before any upgrade.

#### Operator Instruction

```
ACTION: MANUAL ATTRIBUTION REQUIRED for 0x082e843a431aef031264dc232693dd710aedca88

This address is labeled as 'Unknown HYPE Whale' with low confidence.
The entity identity has NOT been established — manual research is required.

STEP 1 — Trusted Primary Source (REQUIRED):
  Find at least ONE verifiable primary source that identifies this address.
  Acceptable: project official docs, exchange/institution label page,
  reputable block explorer label, signed statement, or internal verified record.
  Record findings in: trusted_source_label_value + trusted_source_url_or_note

STEP 2 — Second Source / Cross-Source (REQUIRED):
  Find at least ONE independent secondary or cross-source confirmation.
  Acceptable: analytics dashboard label, cross-source clustering,
  transaction behavior evidence, social identity linkage.
  Record findings in: second_source_label_value + second_source_url_or_note

STEP 3 — Activity Pattern (REQUIRED):
  Document on-chain behavior patterns consistent with the claimed identity.
  Review HyperLiquid position history for consistency.
  Record findings in: activity_pattern_note

STEP 4 — Operator Confirmation (REQUIRED):
  Sign off on the identified label with operator_confirmed_label,
  operator_confidence_assessment, reviewer name, and reviewed_at timestamp.
  Set ready_for_upgrade = true ONLY when ALL evidence is complete.

CRITICAL: This is an UNKNOWN whale. You MUST establish entity identity
before any confidence upgrade can proceed. DO NOT use rejected sources
(unsourced social posts, anonymous claims, AI attributions, screenshots
without URLs, stale labels, TG/chat labels, or vague whale claims).

After completing workbook fields, rerun gates in order (see next_gate_commands).
```

---

### 2. Unknown Hyperliquid Whale

- **Address**: `0x50b309f78e774a756a2230e1769729094cac9f20`
- **Current Confidence**: low
- **Action Type**: manual_attribution_required
- **Priority**: high
- **Blocked Stage**: intake_gate
- **Workbook Row Hint**: Row 3 in v115F workbook (CSV row 3, 1-based data row 2)

#### Blocked Reasons

- INTAKE_GATE_NOT_READY
- WORKFLOW_BLOCKED

#### Missing Workbook Fields

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

#### Recommended Source Types

**Primary Sources (at least 1 required):**
- Project/Team Official Docs or Disclosure (primary_project_official_docs)
- Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- Reputable Block Explorer Label (primary_reputable_explorer_label)
- Public Signed Statement by Entity/Operator (primary_signed_statement)
- Internally Verified Historical Label Record (primary_internal_verified_label)

**Secondary Sources (at least 1 required):**
- Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- Public Social Identity Linkage (secondary_social_identity_linkage)
- Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

**Activity Sources (at least 1 required):**
- Consistent Counterparty Pattern (activity_counterparty_pattern)
- Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- Position Behavior Consistency (activity_position_consistency)
- Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

> For unknown whale: MUST provide trusted primary source + second source/cross-source + activity pattern + operator confirmation. At least one primary_source is required before any upgrade.

#### Operator Instruction

```
ACTION: MANUAL ATTRIBUTION REQUIRED for 0x50b309f78e774a756a2230e1769729094cac9f20

This address is labeled as 'Unknown Hyperliquid Whale' with low confidence.
The entity identity has NOT been established — manual research is required.

STEP 1 — Trusted Primary Source (REQUIRED):
  Find at least ONE verifiable primary source that identifies this address.
  Acceptable: project official docs, exchange/institution label page,
  reputable block explorer label, signed statement, or internal verified record.
  Record findings in: trusted_source_label_value + trusted_source_url_or_note

STEP 2 — Second Source / Cross-Source (REQUIRED):
  Find at least ONE independent secondary or cross-source confirmation.
  Acceptable: analytics dashboard label, cross-source clustering,
  transaction behavior evidence, social identity linkage.
  Record findings in: second_source_label_value + second_source_url_or_note

STEP 3 — Activity Pattern (REQUIRED):
  Document on-chain behavior patterns consistent with the claimed identity.
  Review HyperLiquid position history for consistency.
  Record findings in: activity_pattern_note

STEP 4 — Operator Confirmation (REQUIRED):
  Sign off on the identified label with operator_confirmed_label,
  operator_confidence_assessment, reviewer name, and reviewed_at timestamp.
  Set ready_for_upgrade = true ONLY when ALL evidence is complete.

CRITICAL: This is an UNKNOWN whale. You MUST establish entity identity
before any confidence upgrade can proceed. DO NOT use rejected sources
(unsourced social posts, anonymous claims, AI attributions, screenshots
without URLs, stale labels, TG/chat labels, or vague whale claims).

After completing workbook fields, rerun gates in order (see next_gate_commands).
```

---

## Medium Priority Actions (Corroboration Required)

**Count**: 2

These addresses have medium confidence labels. Additional corroborating evidence is needed
to reach high confidence. They CANNOT go directly to TG test group.

### 1. Matrixport Related

- **Address**: `0x6c8512516ce5669d35113a11ca8b8de322fd84f6`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium
- **Blocked Stage**: intake_gate
- **Workbook Row Hint**: Row 4 in v115F workbook (CSV row 4, 1-based data row 3)

#### Blocked Reasons

- INTAKE_GATE_NOT_READY
- WORKFLOW_BLOCKED

#### Missing Workbook Fields

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

#### Recommended Source Types

**Primary Sources (at least 1 required):**
- Project/Team Official Docs or Disclosure (primary_project_official_docs)
- Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- Reputable Block Explorer Label (primary_reputable_explorer_label)
- Public Signed Statement by Entity/Operator (primary_signed_statement)
- Internally Verified Historical Label Record (primary_internal_verified_label)

**Secondary Sources (at least 1 required):**
- Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- Public Social Identity Linkage (secondary_social_identity_linkage)
- Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

**Activity Sources (at least 1 required):**
- Consistent Counterparty Pattern (activity_counterparty_pattern)
- Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- Position Behavior Consistency (activity_position_consistency)
- Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

> For medium confidence: need full HC_REQ checklist completion. Primary + secondary + activity + operator confirmation all required before upgrade to high.

#### Operator Instruction

```
ACTION: CORROBORATION REQUIRED for 0x6c8512516ce5669d35113a11ca8b8de322fd84f6

This address is labeled as 'Matrixport Related' with medium confidence.
The label is at medium confidence — additional corroborating evidence is needed
to reach high confidence before any TG test group delivery.

STEP 1 — Verify Existing Primary Source (REQUIRED):
  Confirm the existing label source is valid and verifiable.
  If no primary source exists yet, find at least ONE verifiable primary source.
  Record findings in: trusted_source_label_value + trusted_source_url_or_note

STEP 2 — Add Corroborating Secondary Source (REQUIRED):
  Find at least ONE independent secondary source confirming the label.
  Cross-reference: analytics dashboards, cross-source clustering,
  transaction behavior, social identity linkage.
  Record findings in: second_source_label_value + second_source_url_or_note

STEP 3 — Document Activity Pattern (REQUIRED):
  Review and document HyperLiquid position history for consistency.
  Note any behavioral patterns matching the claimed entity.
  Record findings in: activity_pattern_note

STEP 4 — Operator Confirmation (REQUIRED):
  Explicitly confirm the label with operator_confirmed_label,
  operator_confidence_assessment, reviewer name, and reviewed_at timestamp.
  Set ready_for_upgrade = true ONLY when ALL HC_REQ_001 through HC_REQ_009 pass.

IMPORTANT: Medium confidence labels CANNOT go directly to TG test group.
You MUST complete the full evidence checklist and rerun all gates.
DO NOT use rejected sources as core evidence.

After completing workbook fields, rerun gates in order (see next_gate_commands).
```

---

### 2. loraclexyz

- **Address**: `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae`
- **Current Confidence**: medium
- **Action Type**: corroboration_required
- **Priority**: medium
- **Blocked Stage**: intake_gate
- **Workbook Row Hint**: Row 5 in v115F workbook (CSV row 5, 1-based data row 4)

#### Blocked Reasons

- INTAKE_GATE_NOT_READY
- WORKFLOW_BLOCKED

#### Missing Workbook Fields

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

#### Recommended Source Types

**Primary Sources (at least 1 required):**
- Project/Team Official Docs or Disclosure (primary_project_official_docs)
- Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)
- Reputable Block Explorer Label (primary_reputable_explorer_label)
- Public Signed Statement by Entity/Operator (primary_signed_statement)
- Internally Verified Historical Label Record (primary_internal_verified_label)

**Secondary Sources (at least 1 required):**
- Reputable Analytics Dashboard Label (secondary_analytics_dashboard)
- Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)
- Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)
- Public Social Identity Linkage (secondary_social_identity_linkage)
- Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)

**Activity Sources (at least 1 required):**
- Consistent Counterparty Pattern (activity_counterparty_pattern)
- Repeated Asset/Venue Pattern (activity_asset_venue_pattern)
- Position Behavior Consistency (activity_position_consistency)
- Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)

> For medium confidence: need full HC_REQ checklist completion. Primary + secondary + activity + operator confirmation all required before upgrade to high.

#### Operator Instruction

```
ACTION: CORROBORATION REQUIRED for 0x8def9f50456c6c4e37fa5d3d57f108ed23992dae

This address is labeled as 'loraclexyz' with medium confidence.
The label is at medium confidence — additional corroborating evidence is needed
to reach high confidence before any TG test group delivery.

STEP 1 — Verify Existing Primary Source (REQUIRED):
  Confirm the existing label source is valid and verifiable.
  If no primary source exists yet, find at least ONE verifiable primary source.
  Record findings in: trusted_source_label_value + trusted_source_url_or_note

STEP 2 — Add Corroborating Secondary Source (REQUIRED):
  Find at least ONE independent secondary source confirming the label.
  Cross-reference: analytics dashboards, cross-source clustering,
  transaction behavior, social identity linkage.
  Record findings in: second_source_label_value + second_source_url_or_note

STEP 3 — Document Activity Pattern (REQUIRED):
  Review and document HyperLiquid position history for consistency.
  Note any behavioral patterns matching the claimed entity.
  Record findings in: activity_pattern_note

STEP 4 — Operator Confirmation (REQUIRED):
  Explicitly confirm the label with operator_confirmed_label,
  operator_confidence_assessment, reviewer name, and reviewed_at timestamp.
  Set ready_for_upgrade = true ONLY when ALL HC_REQ_001 through HC_REQ_009 pass.

IMPORTANT: Medium confidence labels CANNOT go directly to TG test group.
You MUST complete the full evidence checklist and rerun all gates.
DO NOT use rejected sources as core evidence.

After completing workbook fields, rerun gates in order (see next_gate_commands).
```

---


## Rejected Source Warning

The following evidence sources MUST NOT be used to support label confidence upgrades:

- **Unsourced Social Post** (`rejected_unsourced_social_post`): No verifiable source; social posts alone cannot establish address identity.
- **Single Anonymous Claim** (`rejected_single_anonymous_claim`): Anonymous single-source claim without corroboration is insufficient.
- **AI-Generated Attribution Without Source** (`rejected_ai_attribution`): AI-generated labels hallucinate; source must be independently verifiable.
- **Screenshot Without Verifiable URL or Note** (`rejected_screenshot_without_url`): Screenshots without reproducible evidence are not verifiable.
- **Stale Label Without Update Date** (`rejected_stale_label_no_date`): Stale labels without timestamps may be outdated or incorrect.
- **Label Copied from TG/Chat Without Evidence** (`rejected_tg_chat_label`): Chat-based labels without evidence are hearsay.
- **Vague 'Whale Said to Be X' Style Notes** (`rejected_vague_whale_claim`): Vague claims without specific evidence do not meet any evidence standard.

> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked.
