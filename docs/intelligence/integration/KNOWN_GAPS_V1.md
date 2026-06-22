# Known Gaps — Lane E Integration V1

## Upstream Blocks

| Gap | Impact | Resolution |
|-----|--------|------------|
| Lane A manifest SHA mismatch | Cannot merge Lane A | Lane A needs manifest regeneration at HEAD |
| Lanes B-D remote branches not found | Cannot integrate B/C/D | Await upstream completion |
| Lane A consensus data: 0 records | No consensus-based analysis | Lane A needs consensus provider |
| Lane A PIT quality: all "missing" | PIT analysis limited | Lane A needs PIT quality improvement |

## Research Layer Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| Only 10 sample claims (target: 200+) | P3 quality limited | High (waiting on upstream data) |
| Only 12 evidence edges (target: 400+) | Evidence graph sparse | High |
| Only 3 conflict sets (target: 20+) | Conflict analysis incomplete | Medium |
| Only 10 candidates (target: 15+) | Near target | Low |
| Only 10 dossiers (target: 15+) | Near target | Low |
| No real event data from Lane A | Pipeline uses synthetic samples | High |
| No opposing evidence edges from real data | Anti-pattern detection limited | Medium |

## Test Gaps

| Gap | Impact |
|-----|--------|
| No integration tests yet | Cross-lane reference checks pending |
| No real sample end-to-end test | Requires Lane A-D artifacts |
| No repository-wide matrix test | Final CI gate not run |

## Architecture Gaps

| Gap | Impact |
|-----|--------|
| No producer lock re-validation cron | Needs manual re-check |
| No schema drift detection on existing schemas | Manual verification only |
| No automated calibration scope check | Requires Lane D calibration artifacts |
