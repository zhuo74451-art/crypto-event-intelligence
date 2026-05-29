# Recommendation: **Another Quality Iteration First**

## Rationale
Your metrics hit the gates, but the setup has structural fragility:

- **manual_review_required_rate at 9.95%** is passing but uncomfortably close to the 10% ceilingâone bad macro_policy batch tips you into violation
- **audit_sample_rows=129** barely clears the 100 minimum; statistical confidence is thin
- **zero false positives + zero timezone fails** suggests either excellent data *or* insufficient edge-case coverage (likely the latter given the small sample)
- **auto_publish disabled** is correct, but you're about to add *generation* complexity before proving *review* robustness

---

## Minimum Scope for Next Iteration

**Do this before TG pilot:**

1. **Expand audit_sample to 200â250 rows** (stratified by timezone, asset class, volatility regime)
2. **Inject 10â15 synthetic edge cases** (timezone boundary events, missing data, conflicting signals) into review queue
3. **Re-measure manual_review_required_rate** â target â¤8.5% (buffer room)
4. **Document review failure modes** from the 201 labeled rows (what broke, why)

**Timeline:** 1â2 weeks of data collection + review.

---

## Hard No-Build List

â **Do NOT build yet:**
- TG API integration (wait until review process is bulletproof)
- Draft templating engine (premature; review findings will reshape it)
- Scheduling/batching logic (depends on finalized review SLAs)
- Any persistence layer for drafts (schema will shift)
- Monitoring dashboards for draft metrics (cart before horse)

---

## Green Light Trigger for Pilot

Proceed to **draft-only TG pilot** when:
- manual_review_required_rate â¤8.5% on expanded sample
- Edge-case injection test passes (â¥95% correct handling)
- Review team confirms process is repeatable

Then: **Read-only TG draft generator, no send, 2-week shadow mode.**
