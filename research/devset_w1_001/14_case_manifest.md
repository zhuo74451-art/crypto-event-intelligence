# Case Manifest — w1_001

## Identity

| Field | Value |
|-------|-------|
| sample_id | w1_001 |
| case_branch | workbench/devset-w1-001-v1 |
| protocol_commit | 7382738e8b0bf66fbc42ac8a0df2a8dd75f15513 |
| notion_page_id | 36b0246231d381ce899becc2bbb1ff7c |
| title | Loracle HYPE空单浮亏扩大，持仓规模达1.13亿美元 |

## Object Summary

| Object | ID | File |
|--------|----|------|
| Candidate | cand_w1_001 | `objects/01_candidate.json` |
| Research Unit | ru_w1_001 | `objects/02_research_unit.json` |
| Event Instance | ei_w1_001 | `objects/03_event_instance.json` |
| Claim-Evidence Record | cer_w1_001 | `objects/04_claim_evidence_record.json` |
| Registration | reg_w1_001 | `objects/05_registration.json` |
| Outcome | out_w1_001 | `objects/06_outcome.json` |
| Interference Record | int_w1_001 | `objects/07_interference_record.json` |
| Attribution Assessment | aa_w1_001 | `objects/08_attribution_assessment.json` |

## Key Parameters

| Parameter | Value |
|-----------|-------|
| Information Form | discrete_observable_action |
| Source Medium | onchain_data_feed |
| Selected Clock | information_clock |
| Actual Time Basis | broadcast_time |
| Primary t0 | 2026-05-25T13:02:00Z |
| Primary Window | 1h (t0_to_t_plus_1h) |
| Primary Benchmark | BTC (weak proxy) |
| Sensitivity Benchmark | ETH |
| Data Partition | development |
| t0 Uncertainty | 3600s |
| Separability Status | insufficient_inventory |
| Hard Gates Passed | 2/7 (eligibility + evidence) |
| Attribution Verdict | insufficient_evidence |

## File Structure

```
research/devset_w1_001/
├── objects/
│   ├── 01_candidate.json
│   ├── 02_research_unit.json
│   ├── 03_event_instance.json
│   ├── 04_claim_evidence_record.json
│   ├── 05_registration.json          ← physically separate from Outcome
│   ├── 06_outcome.json               ← physically separate from Registration
│   ├── 07_interference_record.json
│   └── 08_attribution_assessment.json
├── 09_source_material_inventory.md
├── 10_human_judgment_log.md
├── 11_unresolved_questions.md
├── 12_protocol_friction_log.md
├── 13_validation_report.md
└── 14_case_manifest.md
```

## Decision

**READY_TO_BATCH** — All 8 objects created, validated, and consistent. Protocol frictions documented but non-blocking.
