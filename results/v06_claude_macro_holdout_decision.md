# Recommendation: Separate Macro Holdout Queue

## Rule

**Move to `macro_holdout` queue (bypass TG gate):**
- `route_macro_policy=TRUE` AND `asset IS NULL`
- `asset_missing=TRUE` AND event scope spans >3 assets OR explicitly "market-wide"

**Remain in `manual_review_required` (blocks gate):**
- All asset-specific rows (asset IS NOT NULL)
- Ambiguous scope (`scope_ambiguous=TRUE`)
- Low confidence on single-asset events (`low_ai_confidence=TRUE` AND asset IS NOT NULL)

## Risk Controls

1. **Audit trail**: Tag macro_holdout rows with `macro_bypass_v0.6` + timestamp
2. **Velocity gate**: Publish â¤5 macro_holdout events per 24h; flag if exceeded
3. **Confidence floor**: Require `ai_confidence â¥0.72` for macro_holdout auto-publish
4. **Reversion rule**: If macro event later correlates to specific asset, move back to manual_review
5. **Weekly review**: Spot-check 10% of macro_holdout publishes for false positives

## Expected Impact

- `manual_review_required` â ~19 rows (scope_ambiguous + asset-specific)
- **TG gate: 19/201 = 9.45%** â (meets â¤10%)
- Macro events publish with documented risk acceptance

**No trading advice generated from macro_holdout queue.**
