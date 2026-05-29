# Crypto Event Intelligence - TG Draft Pilot Gates

**First Gate (Exact):** `201`

This is your labeled dataset size - the foundational gate for the pilot.

## Recommended Numeric Gates (Sequential):

1. **AI Precision Gate:** `0.87` (minimum confidence threshold)
2. **Manual Queue Gate:** `59` (your existing manual_review_required count)
3. **Audit Sample Gate:** `12` (20% of manual queue: 59 Ã 0.20)
4. **Timezone Error Tolerance:** `Â±2` (hours acceptable drift)
5. **False Positive Threshold:** `0.08` (8% maximum acceptable rate)

**Rationale:** Start with your 201 labeled dataset, route 59 to manual review, sample 12 for audit verification, maintain timezone precision within Â±2 hours, and cap false positives at 8% given auto_publish is disabled.
