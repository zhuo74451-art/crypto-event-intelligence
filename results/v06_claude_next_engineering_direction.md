# Decision: B

## Why This Is The Right Next Step

You have **201 labeled samples with 59 manual_review_required flags**âa 29% friction rate. Before generating *any* TG drafts (even unpublished), you must:

1. **Understand why 29% need manual review.** Are these edge cases, labeling ambiguity, or AI confidence thresholds set too conservatively?
2. **Validate the 0% false_positive_rate claim.** With only 201 samples, this is statistically fragile. The audit_sample=29 is too small to trust production readiness.
3. **Establish rollback/correction workflow.** Once TG drafts exist (even draft-only), correcting mislabeled events becomes operationally expensive. Fix labeling *before* downstream systems depend on it.

**TG draft generation is a *visibility trap*âit feels like progress but amplifies upstream errors at scale.**

---

## What Must NOT Be Built Yet

- â TG draft generator (A) â premature; will expose labeling brittleness in production-like conditions
- â Source reliability scoring (D) â orthogonal; doesn't unblock labeling confidence
- â Backtest expansion (C) â dilutes focus; more bad labels â  better signal
- â Web app / Notion / trading UI â explicitly out of scope

---

## Minimum Implementation Scope (1â2 Days)

1. **Audit the 59 manual_review_required cases:**
   - Categorize: ambiguous event type? timezone edge case? confidence threshold too high?
   - Document top 3 failure modes.

2. **Revalidate false_positive_rate on audit_sample=29:**
   - Manually spot-check all 29; confirm 0% holds or adjust.
   - If <95% confidence, expand audit_sample to n=100.

3. **Tighten AI labeling policy v0.6:**
   - Raise confidence threshold if needed (trade recall for precision).
   - Add explicit rejection rules for ambiguous cases.
   - Document decision boundary.

4. **Establish rollback SOP:**
   - How do you correct a mislabeled event post-TG-draft?
   - Version labeling decisions.

---

## Hard Acceptance Gates

â **Before moving to A (TG drafts):**
- [ ] manual_review_required rate â¤ 10% (or documented + accepted)
- [ ] audit_sample â¥ 100, false_positive_rate â¤ 2%
- [ ] Labeling policy v0.7 documented + tested on holdout set
- [ ] Rollback workflow written (not necessarily automated)

**If any gate fails:** loop B again. Do not proceed to TG drafts.
