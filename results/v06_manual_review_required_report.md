# v0.6 Manual Review Required Audit

manual_review_required_rows: 13

## Top Failure Modes

| mode | count |
|---|---:|
| asset_missing | 10 |
| scope_ambiguous | 9 |
| auto_provisional_needs_audit | 7 |
| low_ai_confidence | 6 |
| route_research_only | 6 |
| medium_confidence_review | 6 |
| route_macro_policy | 2 |

## Interpretation

- These rows should not block AI-first development by default.
- They should be used as audit/holdout examples and rule-improvement input.
- TG draft generation remains delayed until the stricter direction gate passes.
