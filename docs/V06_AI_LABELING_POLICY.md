# v0.6 AI Labeling Policy

Source:

- `results/v06_claude_manual_reduction_response.md`
- `results/v06_claude_tg_pilot_gate.md`

## Decision

Manual labeling is no longer the core operating model.

AI owns the main event-intake workflow. Human review is retained only for:

- low-confidence rows
- audit samples
- rollback investigation
- policy/taxonomy changes

## Ownership Table

| Step | Owner | Threshold | Audit | Rollback |
|---|---|---:|---:|---|
| Candidate classification | AI | 0.85 | 5% weekly | precision < 0.80 |
| Asset attribution | AI | 0.90 | 3% weekly | >2 false positives per 100 |
| Event taxonomy | AI | 0.80 | 10% weekly | taxonomy disagreement > 5% |
| Timezone normalization | AI | 0.99 | 1% spot check | any UTC conversion error |
| Low-risk discard | AI | 0.92 | 2% weekly | >1 false negative per week |
| Publish-review approval | AI + human gate | 0.75 | all rows below 0.75 | manual queue exceeds gate |

## First TG Draft Pilot Gate

This allows draft generation only. It does not allow auto-send or trading advice.

| Gate | Required |
|---|---:|
| labeled_rows | >= 201 |
| manual_review_required_rate | <= 0.085 |
| audit_sample_rows | >= 200 |
| synthetic_edge_cases | >= 15 |
| false_positive_rate | <= 0.02 |
| timezone_fail_count | 0 |
| auto_publish_count | 0 |

## Current Interpretation

The system cannot move toward TG draft pilot until the stricter gate checker passes.

Rows with `manual_review_required=true` remain eligible for review/audit, but they should not block AI-first pipeline development.

## Latest Direction

Claude reviewed the direction again in `results/v06_claude_next_engineering_direction.md` and chose path B:

```text
Continue improving labeling / AI confidence / rollback before TG drafts.
```

Therefore TG draft work is delayed until the stricter gate passes.

## Current Gate Status

As of v0.6, the stricter gate can pass after moving high-confidence macro discard rows into an audit queue. This allows planning for draft-only TG formatting, but does not allow:

- auto-send
- trading advice
- order execution
- unreviewed high-impact publishing
