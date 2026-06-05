# v115R Whale Operator Real Submission Checklist

**Generated**: 2026-06-05T09:38:15.383862+08:00

## ⚠️ READ THIS FIRST — Avoid Common Mistakes

This checklist is for the real operator filling the v115F workbook. It ensures you do NOT accidentally copy TEST_ONLY fixture values or use rejected evidence sources as real evidence.

---

## ❌ TEST_ONLY / Fixture Value Warning

**NEVER copy these values into the real v115F workbook:**

| Contamination Term | Meaning |
|--------------------|---------|
| `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture primary source — NOT real evidence |
| `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture secondary source — NOT real evidence |
| `TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture activity pattern — NOT real evidence |
| `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture operator confirmation — NOT real evidence |
| `TEST_ONLY_REVIEWER` | Fixture reviewer name — use YOUR real identifier |
| `TEST_ONLY_REVIEWED_AT_2026-06-05` | Fixture review timestamp — use real review date |
| `fixture_only` | Marks a value as fixture-only — must be replaced |
| `synthetic` | Synthetic data — must be replaced |
| `mock evidence` | Mock/simulated evidence — must be replaced |

> If the validator detects ANY of these terms in your workbook, `submission_ready` will be `false` and `test_only_or_fixture_contamination_detected` will appear in blocking reasons.

---

## ❌ Rejected Source Warning

The following evidence sources **MUST NOT** be used as core evidence for label confidence upgrades:

1. **Unsourced Social Post** (`rejected_unsourced_social_post`)
2. **Single Anonymous Claim** (`rejected_single_anonymous_claim`)
3. **AI-Generated Attribution Without Source** (`rejected_ai_attribution`)
4. **Screenshot Without Verifiable URL or Note** (`rejected_screenshot_without_url`)
5. **Stale Label Without Update Date** (`rejected_stale_label_no_date`)
6. **Label Copied from TG/Chat Without Evidence** (`rejected_tg_chat_label`)
7. **Vague 'Whale Said to Be X' Style Notes** (`rejected_vague_whale_claim`)

> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked with REJECTED_EVIDENCE_ONLY block reason.

---

## ✅ Allowed Evidence Sources

### Primary Sources (at least 1 required for any high-confidence label)

1. **Project/Team Official Docs or Disclosure** (`primary_project_official_docs`)
2. **Verified Exchange/Institution Address Label Page** (`primary_exchange_institution_label`)
3. **Reputable Block Explorer Label** (`primary_reputable_explorer_label`)
4. **Public Signed Statement by Entity/Operator** (`primary_signed_statement`)
5. **Internally Verified Historical Label Record** (`primary_internal_verified_label`)

### Secondary Sources (at least 1 required)

1. **Reputable Analytics Dashboard Label** (`secondary_analytics_dashboard`)
2. **Cross-Source Wallet Clustering Note** (`secondary_cross_source_clustering`)
3. **Historical Transaction Behavior Evidence** (`secondary_tx_behavior_evidence`)
4. **Public Social Identity Linkage** (`secondary_social_identity_linkage`)
5. **Previous Operator-Reviewed Label Note** (`secondary_operator_reviewed_note`)

### Activity Pattern Sources (at least 1 required)

1. **Consistent Counterparty Pattern** (`activity_counterparty_pattern`)
2. **Repeated Asset/Venue Pattern** (`activity_asset_venue_pattern`)
3. **Position Behavior Consistency** (`activity_position_consistency`)
4. **Historical Interaction with Known Entity Addresses** (`activity_historical_entity_interaction`)

---

## Low / Unknown Whale Address Filling Requirements

For addresses with `current_confidence=low` and labels containing 'Unknown':

| # | Field | Requirement |
|---|-------|-------------|
| 1 | `trusted_source_label_value` | **Required** — real primary source identifying the entity |
| 2 | `trusted_source_url_or_note` | **Required** — verifiable URL or documentation note |
| 3 | `second_source_label_value` | **Required** — independent corroborating source |
| 4 | `second_source_url_or_note` | **Required** — verifiable URL or documentation note |
| 5 | `activity_pattern_note` | **Required** — on-chain behavior patterns consistent with claimed identity |
| 6 | `operator_confirmed_label` | **Required** — confirmed entity label after manual research |
| 7 | `operator_confidence_assessment` | **Required** — confidence assessment based on evidence |
| 8 | `reviewer` | **Required** — your operator/auditor identifier |
| 9 | `reviewed_at` | **Required** — ISO-8601 timestamp of review completion |
| 10 | `ready_for_upgrade` | **Required** — set to `true` after all evidence complete |

**Key rules for low/unknown whales:**

- `action_type` must be `manual_attribution_required`
- Cannot use ANY rejected source as core evidence
- Cannot contain ANY TEST_ONLY value
- Cannot copy fixture evidence values from v115P
- Must not claim real attribution unless source bundle is complete (primary + secondary + activity + operator confirmation)
- At least one `primary_source` is REQUIRED before any upgrade

---

## Medium Confidence Address Filling Requirements

For addresses with `current_confidence=medium`:

| # | Field | Requirement |
|---|-------|-------------|
| 1 | `trusted_source_label_value` | **Required** — existing label source or primary source |
| 2 | `trusted_source_url_or_note` | **Required** — verifiable URL or documentation note |
| 3 | `second_source_label_value` | **Required** — independent corroborating source |
| 4 | `second_source_url_or_note` | **Required** — verifiable URL or documentation note |
| 5 | `activity_pattern_note` | **Required** — on-chain behavior documentation |
| 6 | `operator_confirmed_label` | **Required** — corroborated label after additional evidence |
| 7 | `operator_confidence_assessment` | **Required** — confidence assessment |
| 8 | `reviewer` | **Required** — your operator/auditor identifier |
| 9 | `reviewed_at` | **Required** — ISO-8601 timestamp of review completion |
| 10 | `ready_for_upgrade` | **Required** — set to `true` after all evidence complete |

**Key rules for medium confidence addresses:**

- `action_type` must be `corroboration_required`
- Cannot use ANY rejected source as core evidence
- Cannot contain ANY TEST_ONLY value
- Cannot copy fixture evidence values from v115P
- **Medium passing preflight does NOT equal TG test group readiness**
- Must not claim direct TG readiness
- All HC_REQ_001 through HC_REQ_009 must pass for high confidence upgrade

---

## Reviewer / Reviewed_at / Operator Confirmation Requirements

- `reviewer`: Must be a non-empty operator/auditor identifier (NOT `TEST_ONLY_REVIEWER`)
- `reviewed_at`: Must be a valid ISO-8601 timestamp (NOT `TEST_ONLY_REVIEWED_AT_2026-06-05`)
- `operator_confirmed_label`: Must be a real, researched entity label (NOT a TEST_ONLY fixture value)
- `operator_confidence_assessment`: Must be a real assessment based on evidence (NOT a TEST_ONLY fixture value)
- `ready_for_upgrade`: Must be explicitly `true` after all evidence is complete

---

## Pre-Submission Self-Check

Before submitting the real workbook, verify:

- [ ] ALL 10 operator fields are filled for each of the 4 addresses
- [ ] NO field contains `TEST_ONLY_...` values
- [ ] NO field contains `fixture_only`, `synthetic`, or `mock evidence`
- [ ] NO field references rejected source types (unsourced social post, anonymous claim, AI-generated label, screenshot without URL, stale label, TG chat label, vague claim)
- [ ] Each low/unknown whale has: primary source + secondary source + activity pattern + operator confirmation + reviewer + reviewed_at
- [ ] Each medium confidence address has: existing source or primary source + secondary source + activity pattern + operator confirmation + reviewer + reviewed_at
- [ ] `reviewer` is YOUR real operator identifier
- [ ] `reviewed_at` is the actual date/time you completed the review
- [ ] `operator_confirmed_label` is the actual label you determined through research
- [ ] `operator_confidence_assessment` is your honest assessment
- [ ] `ready_for_upgrade` is set to `true`
- [ ] Medium labels do NOT claim direct TG test group readiness

---

## Safe Rerun Order

After the validator confirms all addresses are `submission_ready=true`, proceed in this exact order:

1. **Run v115O preflight**: `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
2. **Only after preflight passes**, rerun gates in order:
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

**⚠️ Important reminders:**

- **Do NOT skip v115O preflight**. Running gates without preflight pass will result in blocks.
- **Gate order is enforced**: v115G → v115L → v115H → v115M.
- **Medium confidence addresses CANNOT go directly to TG test group**, even if gates pass.
- **All addresses must pass the full HC_REQ_001 through HC_REQ_009 checklist before any TG delivery is considered.**

---

## Validation Command

After filling the workbook, run the validator:

```bash
python scripts/run_market_radar_v115r_whale_operator_real_workbook_submission_validator_and_rerun_plan_local_only.py
```

This will re-check all 4 addresses and produce an updated validation report.
