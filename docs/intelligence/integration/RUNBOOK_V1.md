# Runbook — Lane E Integration V1

## Prerequisites

- Python 3.12+
- pytest 9.1+
- PyYAML

## Quick Start

Run the full Lane E pipeline:

```powershell
python -X utf8 scripts/intelligence/integration/run_lane_e_pipeline.py ^
  --producer-locks docs/execution/lane_e/PRODUCER_LOCKS.yaml ^
  --integration-output data/intelligence/integration ^
  --research-output data/intelligence/research
```

## Individual Steps

### 1. Run Tests
```powershell
python -X utf8 -m pytest tests/intelligence/research/ tests/intelligence/integration/ -q
```

### 2. Run Integration Gates
```powershell
python -X utf8 scripts/intelligence/integration/run_integration_gates.py ^
  --producer-locks docs/execution/lane_e/PRODUCER_LOCKS.yaml
```

### 3. Run Internal Pipeline
```powershell
python -X utf8 market_radar/intelligence/integration/internal_pipeline.py ^
  --producer-locks docs/execution/lane_e/PRODUCER_LOCKS.yaml ^
  --integration-output data/intelligence/integration ^
  --research-output data/intelligence/research
```

### 4. Audit Integrity
```powershell
python -X utf8 scripts/intelligence/research/audit_research_integrity.py
```

## Output Locations

| Artifact | Path |
|----------|------|
| Claims | data/intelligence/research/claims/research_claims_v1.jsonl |
| Evidence Edges | data/intelligence/research/evidence/evidence_edges_v1.jsonl |
| Conflict Sets | data/intelligence/research/conflicts/conflict_sets_v1.jsonl |
| Candidates | data/intelligence/research/candidates/candidate_records_v1.jsonl |
| Dossiers | data/intelligence/research/dossiers/research_dossiers_v1.jsonl |
| Evidence Graph (SQLite) | data/intelligence/research/evidence_graph/evidence_graph_v1.sqlite |
| Integration Runs | data/intelligence/integration/runs/<RUN_ID>/ |

## Recovery

If the pipeline fails mid-run:
1. Check `data/intelligence/integration/runs/<RUN_ID>/pipeline_result.json`
2. Fix the issue
3. Re-run with `--resume` (incremental mode)

## Rollback

Each commit is a checkpoint. To roll back a producer integration:
```powershell
git revert <MERGE_COMMIT_SHA>
```
