# Integration Order v1 — MVP+

## Lane Execution Sequence

```
[STAGE 0] Lane 6: Contract Seal & Worktree Setup
    │
    ▼
[STAGE 1] Lane 1: Hyperliquid Provider ──────────────┐
    │                                                  │
    ▼                                                  │
[STAGE 2] Lane 3: Market Context Provider ────────────┤
    │                                                  │
    ▼                                                  │
[STAGE 3] Lane 4: Existing Feeds ─────────────────────┤
    │                                                  │
    ▼                                                  ▼
[STAGE 4] Lane 2: Whale Engine ←── consumes L1 data ──┤
    │                                                  │
    ▼                                                  ▼
[STAGE 5] Lane 5: Workbench UI ←── consumes all lane outputs
    │
    ▼
[STAGE 6] Lane 6: Integration, QA, Merge
                                                                
[STAGE 7] MVP_READY or ROLLBACK
```

## Dependency Graph

| Lane | Depends On | Provides |
|------|-----------|----------|
| L1 | — | WhalePosition[], WhalePositionChange[] |
| L2 | L1 (whale data) | Risk flags, enriched changes |
| L3 | — | MarketContext[] |
| L4 | — | UnifiedFeedItem[], SourceClaim[] |
| L5 | L1, L2, L3, L4 | Workbench HTML |
| L6 | All | Integration, RunReport, QA verdict |

## Merge Rules

- Each lane pushes to its own feature branch only.
- Lane 6 merges feature branches into integration branch sequentially.
- No lane merges another lane's branch.
- No lane modifies another lane's files.
- Contract changes require Lane 6 approval.

## Testing Gates

Each lane must pass:
1. Its own unit tests
2. Contract validation tests (read-only schemas)
3. Existing baseline tests (no regression)

Lane 6 runs full integration tests before any merge.
