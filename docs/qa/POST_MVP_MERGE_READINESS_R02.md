# Post-MVP Merge Readiness Report R02

Generated: 2026-06-18

## Target Branch Status

| Lane | Branch | Exact SHA | Status | Tests | Security | Evidence |
|------|--------|-----------|--------|-------|----------|----------|
| W1 Operator | post-mvp-operator-workbench-v1 | baf6d537 | READY_FOR_SELECTIVE_INTEGRATION | ≥109 | ✅ | ✅ |
| W2 Whale | post-mvp-whale-portfolio-intelligence-v1 | 0ae76f68 | READY_FOR_SELECTIVE_INTEGRATION | ≥127 | ✅ | ✅ |
| W3 Events | post-mvp-event-clustering-v1 | 97e73100 | READY_FOR_SELECTIVE_INTEGRATION | ≥170 | ✅ | ✅ |
| W4 Market | post-mvp-market-resilience-v1 | 0fe1716d | READY_FOR_SELECTIVE_INTEGRATION | ≥96 | ✅ | ✅ |
| W5 Ops | post-mvp-ops-audit-recovery-v1 | 5dd9b07c | READY_FOR_SELECTIVE_INTEGRATION | ≥151 | ✅ | ✅ |

## Recommended Merge Order

1. **W5 Ops** → foundation (shadow runner, atomic ops, schema)
2. **W4 Market** → adapters (no cross-lane deps)
3. **W2 Whale** → portfolio (depends on W4 adapter interface)
4. **W3 Events** → clustering (depends on W4 market snapshots)
5. **W1 Operator** → integration (depends on W5 shadow, W3 provider)

## Post-Merge Test Sequence

After each merge step, run the corresponding tests:

1. W5: `pytest tests/mvpplus/operations -v` (151+ tests)
2. W4: `unittest discover -s tests/mvpplus/adapters -v` (96+ tests)
3. W2: `pytest tests/mvpplus/whale_domain -v` (127+ tests)
4. W3: `pytest tests/mvpplus/feeds_market_ui -v` (170+ tests)
5. W1: `pytest tests/mvpplus/integration -v` (109+ tests)
6. Combined: `pytest tests/post_mvp/independent_qa -v` (220+ tests)

## Conflict Map

- W5 ↔ W1: run_history schema (parent_run_id, run_kind, run_ordinal)
- W4 ↔ W2: HyperliquidPublicAdapter interface
- W4 ↔ W3: MarketSnapshot model
- W3 ↔ W1: CuratedFeedProvider / FeedItem contract

## Rollback Points

- `b28a240b` — MVPPLUS_READY baseline (independent-qa-v1)
- Each post-MVP commit is individually revertible

## W1 Adaptation Requirements

- W1 must receive updated CuratedFeedProvider from W3
- W1 shadow runner uses W5 run_bounded_shadow with link_existing mode
- run_history schema v2 required for shadow parent/child tracking
