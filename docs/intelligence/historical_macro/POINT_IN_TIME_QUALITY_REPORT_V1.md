# Point-in-Time Quality Report V1

## Summary

| Check | Pass | Fail |
|-------|------|------|
| consensus_before_release | 1658 | 0 |
| published_before_release | 0 | 0 |
| first_seen_before_retrieved | 0 | 0 |
| revision_after_release | 0 | 0 |
| initial_not_overwritten | 0 | 0 |
| current_best_not_in_historical | 0 | 0 |
| missing_consensus_stays_null | 1658 | 0 |
| quality_not_mislabeled | 1658 | 0 |
| source_hash_present | 226 | 0 |
| no_duplicate_event_ids | 1658 | 0 |

**Total Violations**: 0
**Quarantined Records**: 0

## PIT Quality Distribution

All 1,658 release events currently have `point_in_time_quality: "missing"` for consensus.
P0/P1 scope covers official release values only. Pre-event consensus grading is P2 scope.

## Key Findings

1. Zero duplicate event IDs — deterministic ID generation working correctly
2. Zero critical violations — all events pass structural validation
3. Consensus quality grading will improve in P2 when pre-event observations are added
4. Source snapshots all have SHA256 hashes for content verification
