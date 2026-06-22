# Runbook V1 — Lane A: Historical Macro Evidence Factory

## Overview

This Lane builds the historical macro-economic event dataset from public US government data sources.

## Prerequisites

- Python 3.10+
- Network access to: api.bls.gov, fred.stlouisfed.org
- No API keys required for basic operation

## Quick Start

```powershell
cd "C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-a-historical-macro-evidence-v1"

# Full pipeline (release events + dataset + audit + coverage)
python -X utf8 scripts/intelligence/historical_macro/run_lane_a_pipeline.py ^
  --start-date 2010-01-01 --end-date 2026-12-31 ^
  --output-dir data/intelligence/historical_macro

# Individual steps
python -X utf8 scripts/intelligence/historical_macro/build_release_events.py ^
  --start-year=2010 --end-year=2026
python -X utf8 scripts/intelligence/historical_macro/build_macro_evidence_dataset.py
python -X utf8 scripts/intelligence/historical_macro/audit_point_in_time.py
python -X utf8 scripts/intelligence/historical_macro/generate_coverage_report.py
```

## Pipeline Steps

| Step | Script | Description |
|------|--------|-------------|
| 1 | build_release_events.py | Fetches data from BLS and FRED APIs, normalizes to MacroReleaseEventV1 |
| 2 | build_consensus_observations.py | Fetches pre-event consensus from public sources (P2) |
| 3 | build_revision_chains.py | Builds revision history from provider data (P2) |
| 4 | build_macro_evidence_dataset.py | Creates SQLite index and validates all files |
| 5 | audit_point_in_time.py | Runs 10 PIT checks, quarantines violations |
| 6 | generate_coverage_report.py | Generates coverage statistics |

## Output Locations

| Artifact | Path |
|----------|------|
| Release Events (JSONL) | data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl |
| Source Snapshots (JSONL) | data/intelligence/historical_macro/normalized/macro_source_snapshots_v1.jsonl |
| SQLite Index | data/intelligence/historical_macro/indexes/macro_evidence_v1.sqlite |
| PIT Report | data/intelligence/historical_macro/reports/pit_audit_v1.json |
| Coverage Report | data/intelligence/historical_macro/reports/coverage_report_v1.json |

## Recovery

- Pipeline supports `--resume` flag: skips already-fetched events by checking event_id
- To reset: delete `macro_release_events_v1.jsonl` and re-run
- Provider failures are isolated — one provider failing doesn't stop others

## Testing

```powershell
# Run Lane A tests only
python -X utf8 -m pytest tests/intelligence/historical_macro/ -q

# Run with contract tests
python -X utf8 -m pytest tests/intelligence/historical_macro/ tests/intelligence/test_contracts.py -q

# Full intelligence test suite
python -X utf8 -m pytest tests/intelligence/ -q
```

## Network Requirements

- BLS API: api.bls.gov (HTTPS)
- FRED: fred.stlouisfed.org (HTTPS)
- Rate limiting: 0.5s between BLS requests, 1.0s between FRED requests
- Timeout: 30s per request
- Retries: 3 attempts with 2s backoff
