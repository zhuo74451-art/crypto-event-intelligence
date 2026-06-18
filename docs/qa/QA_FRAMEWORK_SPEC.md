# Independent QA Framework — mvpplus

## Purpose

This QA framework provides read-only, deterministic scanning and validation for the mvpplus project. It is independent of business logic and operates on repository structure, source code patterns, and data artifacts.

## Principles

1. **Read-only**: No modification of business code or data.
2. **Deterministic**: Same inputs → same results.
3. **No network by default**: All scanners operate on local files.
4. **Explicit statuses**: PASS / FAIL / BLOCKED / NOT_APPLICABLE.
5. **Evidence binding**: All results are committed as JSON artifacts with commit SHA binding.

## Directory Structure

```
qa/mvpplus/
  qa_core.py               — All scanner implementations
  evidence_schema.json     — Evidence artifact schema
  corpus/
    url_attack_corpus.json
    xss_attack_corpus.json
    path_traversal_corpus.json
    malformed_fixture_corpus.json

scripts/mvpplus/independent_qa/
  run_qa_scan.py           — Main QA scan runner
  verify_evidence.py       — Evidence artifact verifier

tests/mvpplus/independent_qa/
  test_qa_foundation.py    — QA framework tests

docs/qa/
  QA_FRAMEWORK_SPEC.md     — This file
  SCANNER_CATALOG.md       — Scanner reference

artifacts/evidence/
  w6_qa_foundation_report.json  — QA evidence artifact
```

## Scanner Statuses

| Status | Meaning |
|--------|---------|
| PASS | No violations found |
| FAIL | Violations detected |
| BLOCKED | Missing evidence or unreachable input |
| NOT_APPLICABLE | Scanner conditions not met |

## Usage

```bash
# Run full QA scan
python -X utf8 scripts/mvpplus/independent_qa/run_qa_scan.py

# Run with explicit repo and ref
python -X utf8 scripts/mvpplus/independent_qa/run_qa_scan.py \
  --repo /path/to/repo \
  --ref cfc1e09b

# Verify evidence artifact
python -X utf8 scripts/mvpplus/independent_qa/verify_evidence.py \
  artifacts/evidence/w6_qa_foundation_report.json

# Run QA framework tests
python -X utf8 -m pytest tests/mvpplus/independent_qa/ -v
```

## Result Claim Rules

- `QA_FOUNDATION_READY`: QA framework tests pass, branch pushed, worktree clean, no business files changed.
- `MVPPLUS_READY`: Not claimed by this framework.
- `INTERNAL_PRODUCTION_CANDIDATE`: Not claimed by this framework.
