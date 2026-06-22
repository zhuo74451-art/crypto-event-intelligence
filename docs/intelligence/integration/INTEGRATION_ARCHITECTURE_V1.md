# Integration Architecture V1

## Overview

The integration layer (Lane E) is responsible for assembling and auditing Lanes A-D into a unified internal intelligence pipeline. It does NOT modify producer code, merge to main, or deploy to production.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Integration Gates                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │Lock &│ │Contract│ │Single│ │Cross │ │End-to│ │Kernel │ │
│  │Hash  │→│Compat.│→│Lane  │→│Lane  │→│End   │→│Seal   │ │
│  │Check │ │Check │ │Tests │ │Check │ │Sample│ │Check  │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                   Internal Pipeline                       │
│  Macro → Market → Replay → Validation → Research         │
│  (deterministic, idempotent, offline)                     │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                   Output Registry                         │
│  Claims / Evidence / Conflicts / Candidates / Dossiers    │
│  JSONL + SQLite persistence                               │
└─────────────────────────────────────────────────────────┘
```

## Producer Locking

Each producer lane is locked by SHA before integration. Locked SHAs are immutable for the duration of a run.

## Compatibility Checks

16 checks per producer lane, including:
- SHA consistency (base, head, manifest)
- Schema presence and version
- Field format (UTC, deterministic IDs)
- Data integrity (no duplicates, PIT fields present)
- Evidence preservation (failed experiments, abstentions)

## Current Status

| Component | Status |
|-----------|--------|
| Producer Locks | Created, Lane A SHA locked (needs manifest repair) |
| Compatibility Checker | Implemented (16 checks) |
| Integration Gates | 6/6 pass |
| Internal Pipeline | Working (10 claims, 3 conflicts) |
| Run ID Determinism | Verified |
| Lane A Merge | Blocked — manifest SHA mismatch |
| Lanes B/C/D Merge | Blocked — remote branch not found |
